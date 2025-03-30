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

# Configuration
BITRIX_CLIENT_ID = os.getenv('BITRIX_CLIENT_ID')
BITRIX_CLIENT_SECRET = os.getenv('BITRIX_CLIENT_SECRET')
BITRIX_REDIRECT_URI = os.getenv('BITRIX_REDIRECT_URI')
FILE_FIELD_ID = os.getenv('FILE_FIELD_ID')
DATABASE = os.getenv('DATABASE_URL', 'sqlite:///app.db').replace('sqlite:///', '')

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bitrix_tokens (
                access_token TEXT PRIMARY KEY,
                refresh_token TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL
            )
        ''')

init_db()

class BitrixAPI:
    @staticmethod
    def get_token(code):
        response = requests.post(
            "https://oauth.bitrix.info/oauth/token/",
            data={
                'grant_type': 'authorization_code',
                'client_id': BITRIX_CLIENT_ID,
                'client_secret': BITRIX_CLIENT_SECRET,
                'redirect_uri': BITRIX_REDIRECT_URI,
                'code': code
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def refresh_token(refresh_token):
        logger.info("🔁 Обновляем access_token через refresh_token...")
        response = requests.post(
            "https://oauth.bitrix.info/oauth/token/",
            data={
                'grant_type': 'refresh_token',
                'client_id': BITRIX_CLIENT_ID,
                'client_secret': BITRIX_CLIENT_SECRET,
                'refresh_token': refresh_token
            },
            timeout=10
        )
        response.raise_for_status()
        refreshed = response.json()
        logger.info(f"✅ Новый access_token: {refreshed.get('access_token')}")
        return refreshed

    @staticmethod
    def get_valid_token():
        with sqlite3.connect(DATABASE) as conn:
            row = conn.execute(
                'SELECT access_token, refresh_token, expires_at FROM bitrix_tokens'
            ).fetchone()

            if row:
                logger.info(f"🧾 Найден токен. expires_at = {row[2]}")
                if datetime.fromisoformat(row[2]) > datetime.now():
                    return {
                        'access_token': row[0],
                        'refresh_token': row[1],
                        'expires_at': row[2]
                    }
                else:
                    logger.warning("⚠️ Токен просрочен, обновляем...")
                    new_token = BitrixAPI.refresh_token(row[1])
                    expires_at = datetime.now() + timedelta(seconds=new_token['expires_in'] - 60)
                    conn.execute('DELETE FROM bitrix_tokens')
                    conn.execute(
                        'INSERT INTO bitrix_tokens VALUES (?, ?, ?)',
                        (new_token['access_token'], new_token['refresh_token'], expires_at.isoformat())
                    )
                    return new_token

            logger.error("❌ Нет токенов в базе данных")
            raise ValueError("No tokens available in database")

    @staticmethod
    def api_call(method, params=None):
        token_data = BitrixAPI.get_valid_token()
        headers = {
            'Authorization': f'Bearer {token_data["access_token"]}',
            'Content-Type': 'application/json'
        }
        response = requests.post(
            f"https://vas-dom.bitrix24.ru/rest/1/{method}",
            json=params,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        return response.json()

@app.route('/')
def index():
    return "Service is running ✅", 200

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
            conn.execute(
                'INSERT INTO bitrix_tokens VALUES (?, ?, ?)',
                (token_data['access_token'], token_data['refresh_token'], expires_at.isoformat())
            )

        logger.info("✅ Авторизация прошла успешно")
        logger.info(f"🔐 Access token: {token_data['access_token']}")
        logger.info(f"🔁 Refresh token: {token_data['refresh_token']}")
        logger.info(f"⏳ Expires at: {expires_at.isoformat()}")

        return jsonify({"status": "Authorization successful"}), 200
    except Exception as e:
        logger.exception("🔥 Ошибка при сохранении токена")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/webhook/disk', methods=['POST'])
def handle_disk_webhook():
    data = request.get_json()

    required_fields = ['folder_id', 'deal_id', 'file_ids']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    threading.Thread(
        target=process_files,
        args=(data['folder_id'], data['deal_id'], data['file_ids'])
    ).start()

    return jsonify({"status": "processing_started"}), 202

def process_files(folder_id, deal_id, file_ids):
    logger.info(f"📦 Обработка {len(file_ids)} файлов для сделки {deal_id}")
    files = []
    for file_id in file_ids:
        file_info = BitrixAPI.api_call('disk.file.get', {'id': file_id})
        if file_info.get('result'):
            files.append({
                'file_id': file_id,
                'name': file_info['result'].get('NAME', '')
            })

    if files:
        update_data = {
            'id': deal_id,
            'fields': {
                FILE_FIELD_ID: [{'fileId': f['file_id']} for f in files]
            }
        }
        result = BitrixAPI.api_call('crm.deal.update', update_data)

        if result.get('result'):
            logger.info(f"✅ Сделка {deal_id} успешно обновлена")
        else:
            logger.error(f"❌ Ошибка обновления сделки {deal_id}: {result.get('error', 'Unknown error')}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)), threaded=True)
