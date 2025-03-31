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

BITRIX_CLIENT_ID = os.getenv('BITRIX_CLIENT_ID')
BITRIX_CLIENT_SECRET = os.getenv('BITRIX_CLIENT_SECRET')
BITRIX_REDIRECT_URI = os.getenv('BITRIX_REDIRECT_URI')
FILE_FIELD_ID = os.getenv('FILE_FIELD_ID')
FOLDER_FIELD_ID = os.getenv('FOLDER_FIELD_ID')
DATABASE = os.getenv('DATABASE_URL', 'sqlite:///app.db').replace('sqlite:///', '')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
        url = f"https://vas-dom.bitrix24.ru/rest/{method}"
        response = requests.post(url, json=params, headers=headers)
        response.raise_for_status()
        return response.json()

def transform_bitrix_data(data):
    if isinstance(data, dict):
        return {k: transform_bitrix_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [transform_bitrix_data(item) for item in data]
    elif isinstance(data, str) and data.startswith('{=') and data.endswith('}'):
        inner = data[2:-1]
        if '.' in inner:
            return inner.split('.')[-1]
        else:
            return inner
    return data

@app.route('/webhook/disk', methods=['POST'])
def handle_disk_webhook():
    try:
        raw_data = request.data.decode('utf-8')
        logger.info(f"📥 Входящий JSON: {raw_data}")

        clean_data = re.sub(r'//.*', '', raw_data)
        clean_data = re.sub(r'/\*.*?\*/', '', clean_data, flags=re.DOTALL)
        data = json.loads(clean_data)

        transformed_data = transform_bitrix_data(data)
        logger.info(f"🧾 Преобразованные данные: {transformed_data}")

        deal_id = transformed_data.get('deal_id')
        if not deal_id:
            return jsonify({"error": "Missing deal_id"}), 400

        deal = BitrixAPI.api_call('crm.deal.get', {'id': deal_id})
        folder_id = deal['result'].get(FOLDER_FIELD_ID)
        if not folder_id:
            return jsonify({"error": "folder_id not found in deal"}), 400

        folder_data = BitrixAPI.api_call('disk.folder.getchildren', {'id': folder_id})
        file_ids = [item['ID'] for item in folder_data.get('result', []) if item['TYPE'] == 'file']

        if not file_ids:
            return jsonify({"error": "No files found in folder"}), 400

        threading.Thread(target=process_files, args=(folder_id, deal_id, file_ids), daemon=True).start()
        return jsonify({"status": "processing_started", "files": file_ids}), 202

    except Exception as e:
        logger.exception(f"🔥 Ошибка при обработке webhook: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def process_files(folder_id, deal_id, file_ids):
    try:
        logger.info(f"🚀 Обработка файлов: {file_ids} для сделки {deal_id}")
        files = [{'fileId': fid} for fid in file_ids]
        result = BitrixAPI.api_call('crm.deal.update', {'id': deal_id, 'fields': {FILE_FIELD_ID: files}})
        logger.info(f"📤 Результат обновления сделки: {json.dumps(result, ensure_ascii=False)}")
    except Exception as e:
        logger.exception(f"🔥 Ошибка обработки файлов: {str(e)}")

@app.route('/')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)), debug=False)
