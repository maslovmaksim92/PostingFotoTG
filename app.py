import os
import re
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)

# Конфигурация
BITRIX_CLIENT_ID = os.getenv('BITRIX_CLIENT_ID')
BITRIX_CLIENT_SECRET = os.getenv('BITRIX_CLIENT_SECRET')
BITRIX_REDIRECT_URI = os.getenv('BITRIX_REDIRECT_URI')
FILE_FIELD_ID = os.getenv('FILE_FIELD_ID')
FOLDER_FIELD_ID = os.getenv('FOLDER_FIELD_ID')
DATABASE = os.getenv('DATABASE_URL', 'sqlite:///app.db').replace('sqlite:///', '')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация БД
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bitrix_tokens (
                access_token TEXT PRIMARY KEY,
                refresh_token TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL
            )
        ''')
        conn.commit()

init_db()

class BitrixAPI:

    @staticmethod
    def execute_request(url, data):
        try:
            logger.info(f"🔄 Отправка запроса на {url} с данными: {data}")
            response = requests.post(url, data=data, timeout=10)
            logger.info(f"📩 Ответ: {response.status_code} - {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка запроса: {str(e)}")
            raise

    @classmethod
    def get_token(cls, code):
        return cls.execute_request("https://oauth.bitrix.info/oauth/token/", {
            'grant_type': 'authorization_code',
            'client_id': BITRIX_CLIENT_ID,
            'client_secret': BITRIX_CLIENT_SECRET,
            'redirect_uri': BITRIX_REDIRECT_URI,
            'code': code
        })

    @classmethod
    def refresh_token(cls, refresh_token):
        return cls.execute_request("https://oauth.bitrix.info/oauth/token/", {
            'grant_type': 'refresh_token',
            'client_id': BITRIX_CLIENT_ID,
            'client_secret': BITRIX_CLIENT_SECRET,
            'refresh_token': refresh_token
        })

    @classmethod
    def get_valid_token(cls):
        with sqlite3.connect(DATABASE) as conn:
            row = conn.execute('SELECT access_token, refresh_token, expires_at FROM bitrix_tokens').fetchone()

            if row and datetime.fromisoformat(row[2]) > datetime.now():
                logger.info("🔐 Используется актуальный access_token из БД")
                return {'access_token': row[0], 'refresh_token': row[1]}

            if row:
                logger.info("🔄 Access token истек, пробуем обновить через refresh_token")
                new_token = cls.refresh_token(row[1])
                expires_at = datetime.now() + timedelta(seconds=new_token['expires_in'] - 60)
                conn.execute('DELETE FROM bitrix_tokens')
                conn.execute('INSERT INTO bitrix_tokens VALUES (?, ?, ?)',
                             (new_token['access_token'], new_token['refresh_token'], expires_at.isoformat()))
                conn.commit()
                logger.info("✅ Новый access_token сохранён")
                return new_token

            logger.error("❌ Токены отсутствуют в базе данных")
            raise ValueError("Отсутствуют токены в базе данных")

    @classmethod
    def api_call(cls, method, params=None):
        token = cls.get_valid_token()
        headers = {'Authorization': f'Bearer {token["access_token"]}', 'Content-Type': 'application/json'}
        url = f"https://vas-dom.bitrix24.ru/rest/{method}"
        logger.info(f"📡 API вызов: {url} | Параметры: {params}")
        response = requests.post(url, json=params, headers=headers)
        logger.info(f"📬 Ответ API: {response.status_code} | {response.text}")
        response.raise_for_status()
        return response.json()

@app.route('/')
def health_check():
    logger.info("💓 Проверка работоспособности сервиса")
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()}), 200

@app.route('/oauth/callback')
def oauth_callback():
    code = request.args.get('code')
    if not code:
        logger.warning("⚠️ Пустой код авторизации")
        return jsonify({"error": "Authorization code missing"}), 400

    token_data = BitrixAPI.get_token(code)
    expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'] - 60)

    with sqlite3.connect(DATABASE) as conn:
        conn.execute('DELETE FROM bitrix_tokens')
        conn.execute('INSERT INTO bitrix_tokens VALUES (?, ?, ?)',
                     (token_data['access_token'], token_data['refresh_token'], expires_at.isoformat()))
        conn.commit()

    logger.info("✅ Авторизация прошла успешно")
    logger.info(f"🔐 Access token: {token_data['access_token']}")
    logger.info(f"🔁 Refresh token: {token_data['refresh_token']}")
    logger.info(f"⏳ Expires at: {expires_at.isoformat()}")

    return jsonify({"status": "Authorization successful"}), 200

@app.route('/webhook/disk', methods=['POST'])
def handle_disk_webhook():
    data = request.get_json()
    logger.info(f"📥 Входящий JSON: {json.dumps(data, ensure_ascii=False)}")

    required_fields = ['deal_id']
    if not data or not all(field in data for field in required_fields):
        logger.error(f"❌ Отсутствуют обязательные поля: {data}")
        return jsonify({"error": "Missing required fields"}), 400

    try:
        deal_id = data['deal_id']

        # Обработка шаблонных переменных: {=Document.ID} → ID
        if isinstance(deal_id, str) and deal_id.startswith('{=') and deal_id.endswith('}'):
            inner = deal_id[2:-1]
            deal_id = inner.split('.')[-1] if '.' in inner else inner
            logger.info(f"🔄 Обработан шаблонный deal_id: {deal_id}")

        deal = BitrixAPI.api_call('crm.deal.get', {'id': deal_id})
        folder_id = deal['result'].get(FOLDER_FIELD_ID)

        if not folder_id:
            logger.error(f"❌ Не удалось получить folder_id из поля {FOLDER_FIELD_ID} в сделке {deal_id}")
            return jsonify({"error": "folder_id not found in deal"}), 400

        logger.info(f"📁 Получен folder_id из сделки: {folder_id}")

        folder_data = BitrixAPI.api_call('disk.folder.getchildren', {'id': folder_id})
        logger.info(f"📂 Ответ по содержимому папки: {json.dumps(folder_data, ensure_ascii=False)}")

        file_ids = [item['ID'] for item in folder_data.get('result', []) if item['TYPE'] == 'file']

        if not file_ids:
            logger.warning(f"⚠️ В папке {folder_id} нет файлов для обработки")
            return jsonify({"error": "No files found in folder"}), 400

        threading.Thread(target=process_files, args=(folder_id, deal_id, file_ids), daemon=True).start()
        return jsonify({"status": "processing_started", "files": file_ids}), 202

    except Exception as e:
        logger.exception(f"🔥 Ошибка при обработке webhook: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def process_files(folder_id, deal_id, file_ids):
    try:
        logger.info(f"🚀 Начата обработка файлов для сделки {deal_id}, folder_id: {folder_id}, всего файлов: {len(file_ids)}")

        files = []
        for fid in file_ids:
            try:
                file_info = BitrixAPI.api_call('disk.file.get', {'id': fid})
                if file_info.get('result'):
                    files.append({'fileId': fid})
                    logger.info(f"📄 Найден файл ID {fid}: {file_info['result'].get('NAME')} | Размер: {file_info['result'].get('SIZE')} байт")
                else:
                    logger.warning(f"⚠️ Пустой результат от API по файлу {fid}")
            except Exception as e:
                logger.error(f"❌ Ошибка получения данных по файлу {fid}: {e}")

        if not files:
            logger.warning(f"⚠️ Нет валидных файлов для прикрепления к сделке {deal_id}")
            return

        update_data = {'id': deal_id, 'fields': {FILE_FIELD_ID: files}}
        result = BitrixAPI.api_call('crm.deal.update', update_data)
        logger.info(f"📤 Ответ от crm.deal.update: {json.dumps(result, ensure_ascii=False)}")

        if result.get('result'):
            logger.info(f"✅ Сделка {deal_id} успешно обновлена с {len(files)} файлами")
        else:
            logger.error(f"❌ Ошибка обновления сделки {deal_id}: {result.get('error')} | Запрос: {update_data}")

    except Exception as e:
        logger.exception(f"🔥 Критическая ошибка при обработке файлов: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)), threaded=True, debug=False)
