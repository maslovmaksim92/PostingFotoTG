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

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__)

# Конфигурация
BITRIX_CLIENT_ID = os.getenv('BITRIX_CLIENT_ID')
BITRIX_CLIENT_SECRET = os.getenv('BITRIX_CLIENT_SECRET')
BITRIX_REDIRECT_URI = os.getenv('BITRIX_REDIRECT_URI')
FILE_FIELD_ID = os.getenv('FILE_FIELD_ID')
FOLDER_FIELD_ID = os.getenv('FOLDER_FIELD_ID')
DATABASE = os.getenv('DATABASE_URL', 'sqlite:///app.db').replace('sqlite:///', '')

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log", encoding='utf-8'),
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
            logger.info(f"🔄 Отправка запроса: {url} | data: {data}")
            response = requests.post(url, data=data, timeout=10)
            logger.info(f"📩 Ответ: {response.status_code} | {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Ошибка запроса: {e}")
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
                logger.info("🔐 Используется access_token из БД")
                return {'access_token': row[0], 'refresh_token': row[1]}
            if row:
                logger.info("🔄 Обновляем access_token")
                new_token = cls.refresh_token(row[1])
                expires_at = datetime.now() + timedelta(seconds=new_token['expires_in'] - 60)
                conn.execute('DELETE FROM bitrix_tokens')
                conn.execute('INSERT INTO bitrix_tokens VALUES (?, ?, ?)', (
                    new_token['access_token'], new_token['refresh_token'], expires_at.isoformat()
                ))
                conn.commit()
                return new_token
            raise ValueError("Отсутствуют токены в базе данных")

    @classmethod
    def api_call(cls, method, params=None):
        token = cls.get_valid_token()
        headers = {'Authorization': f'Bearer {token["access_token"]}', 'Content-Type': 'application/json'}
        url = f"https://vas-dom.bitrix24.ru/rest/{method}"
        logger.info(f"📡 Bitrix API call: {url} | params: {params}")
        response = requests.post(url, json=params, headers=headers)
        logger.info(f"📬 API response: {response.status_code} | {response.text}")
        response.raise_for_status()
        return response.json()

@app.route('/')
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})

@app.route('/oauth/callback')
def oauth_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "Authorization code missing"}), 400
    try:
        token_data = BitrixAPI.get_token(code)
        expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'] - 60)
        with sqlite3.connect(DATABASE) as conn:
            conn.execute('DELETE FROM bitrix_tokens')
            conn.execute('INSERT INTO bitrix_tokens VALUES (?, ?, ?)', (
                token_data['access_token'], token_data['refresh_token'], expires_at.isoformat()
            ))
            conn.commit()
        logger.info("✅ Авторизация успешна")
        return jsonify({"status": "Authorization successful"}), 200
    except Exception as e:
        logger.exception("❌ Ошибка в oauth_callback")
        return jsonify({"error": str(e)}), 500

@app.route('/webhook/disk', methods=['POST'])
def handle_disk_webhook():
    try:
        raw_data = request.data.decode('utf-8')
        logger.info(f"📥 Входящий JSON: {raw_data}")
        data = json.loads(re.sub(r'/\*.*?\*/|//.*', '', raw_data, flags=re.DOTALL))
        deal_id = extract_field(data.get('deal_id'))
        if not deal_id:
            return jsonify({"error": "Invalid deal_id"}), 400

        deal = BitrixAPI.api_call('crm.deal.get', {'id': deal_id})
        folder_id = deal['result'].get(FOLDER_FIELD_ID)
        if not folder_id:
            logger.error(f"❌ Не найден folder_id в сделке")
            return jsonify({"error": "folder_id not found"}), 400

        logger.info(f"📁 Получен folder_id: {folder_id}")
        folder_data = BitrixAPI.api_call('disk.folder.getchildren', {'id': folder_id})
        file_ids = [item['ID'] for item in folder_data.get('result', []) if item['TYPE'] == 'file']
        if not file_ids:
            return jsonify({"error": "No files in folder"}), 400

        threading.Thread(target=process_files, args=(folder_id, deal_id, file_ids), daemon=True).start()
        return jsonify({"status": "processing_started", "files": file_ids}), 202

    except Exception as e:
        logger.exception(f"🔥 Ошибка в handle_disk_webhook: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def extract_field(value):
    if isinstance(value, str) and value.startswith('{=') and value.endswith('}'):
        cleaned = value[2:-1]
        return cleaned.split('.')[-1]
    return value

def process_files(folder_id, deal_id, file_ids):
    try:
        files = []
        for fid in file_ids:
            try:
                file_info = BitrixAPI.api_call('disk.file.get', {'id': fid})
                if file_info.get('result'):
                    files.append({'fileId': fid})
                    logger.info(f"📎 Файл: {file_info['result'].get('NAME')} добавлен")
            except Exception as e:
                logger.warning(f"❗ Ошибка по файлу {fid}: {e}")

        if files:
            update = {'id': deal_id, 'fields': {FILE_FIELD_ID: files}}
            result = BitrixAPI.api_call('crm.deal.update', update)
            logger.info(f"📤 Результат обновления сделки: {result}")
        else:
            logger.warning("❌ Нет файлов для прикрепления")
    except Exception as e:
        logger.exception(f"💥 Ошибка в process_files: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)), debug=False)
