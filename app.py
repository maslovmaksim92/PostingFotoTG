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
            response = requests.post(url, data=data, timeout=10)
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
                return {'access_token': row[0], 'refresh_token': row[1]}

            if row:
                new_token = cls.refresh_token(row[1])
                expires_at = datetime.now() + timedelta(seconds=new_token['expires_in'] - 60)
                conn.execute('DELETE FROM bitrix_tokens')
                conn.execute('INSERT INTO bitrix_tokens VALUES (?, ?, ?)',
                             (new_token['access_token'], new_token['refresh_token'], expires_at.isoformat()))
                conn.commit()
                return new_token

            raise ValueError("Отсутствуют токены в базе данных")

    @classmethod
    def api_call(cls, method, params=None):
        token = cls.get_valid_token()
        headers = {'Authorization': f'Bearer {token["access_token"]}', 'Content-Type': 'application/json'}
        response = requests.post(f"https://vas-dom.bitrix24.ru/rest/1/{method}", json=params, headers=headers)
        response.raise_for_status()
        return response.json()

@app.route('/')
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()}), 200

@app.route('/oauth/callback')
def oauth_callback():
    code = request.args.get('code')
    if not code:
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

    required_fields = ['folder_id', 'deal_id']
    if not data or not all(field in data for field in required_fields):
        logger.error(f"❌ Отсутствуют обязательные поля: {data}")
        return jsonify({"error": "Missing required fields"}), 400

    if not isinstance(data['folder_id'], str) or not data['folder_id']:
        logger.warning("⚠️ folder_id отсутствует или не строка")
        return jsonify({"error": "Invalid or missing folder_id"}), 400

    threading.Thread(target=process_files, args=(data['folder_id'], data['deal_id']), daemon=True).start()
    return jsonify({"status": "processing_started"}), 202

def process_files(folder_id, deal_id):
    try:
        logger.info(f"🚀 Запуск process_files для folder_id={folder_id}, deal_id={deal_id}")
        # Получение всех файлов в папке
        folder_content = BitrixAPI.api_call('disk.folder.getchildren', {'id': folder_id})
        items = folder_content.get('result', [])
        logger.info(f"📂 Найдено {len(items)} объектов в папке")

        files = []
        for item in items:
            if item.get('TYPE') == 'file':
                file_id = item['ID']
                files.append({'fileId': file_id})
                logger.info(f"📎 Добавлен файл ID={file_id}, имя: {item.get('NAME')}")

        if not files:
            logger.warning("⚠️ В папке нет файлов для прикрепления")
            return

        update_data = {'id': deal_id, 'fields': {FILE_FIELD_ID: files}}
        result = BitrixAPI.api_call('crm.deal.update', update_data)

        if result.get('result'):
            logger.info(f"✅ Файлы успешно прикреплены к сделке {deal_id}")
        else:
            logger.error(f"❌ Ошибка обновления сделки: {result.get('error')} | Запрос: {update_data}")

    except Exception as e:
        logger.exception(f"🔥 Критическая ошибка в process_files: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)), threaded=True, debug=True)
