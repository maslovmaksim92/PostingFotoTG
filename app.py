import os
import re
import json
import logging
import sqlite3
import threading
from flask import Flask, request, jsonify
from requests.auth import HTTPBasicAuth
import requests
from urllib.parse import urlencode
from datetime import datetime, timedelta

app = Flask(__name__)

# Конфигурация из переменных окружения
BITRIX_CLIENT_ID = os.getenv('BITRIX_CLIENT_ID')
BITRIX_CLIENT_SECRET = os.getenv('BITRIX_CLIENT_SECRET')
BITRIX_REDIRECT_URI = os.getenv('BITRIX_REDIRECT_URI')
BASIC_AUTH = HTTPBasicAuth(os.getenv('BASIC_AUTH_LOGIN'), os.getenv('BASIC_AUTH_PASSWORD'))
FILE_FIELD_ID = os.getenv('FILE_FIELD_ID')
FOLDER_FIELD_ID = os.getenv('FOLDER_FIELD_ID')

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация БД
def init_db():
    with sqlite3.connect('app.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bitrix_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL
            )
        ''')
init_db()

class BitrixAPI:
    @staticmethod
    def get_auth_url():
        params = {
            'client_id': BITRIX_CLIENT_ID,
            'redirect_uri': BITRIX_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'crm,disk'
        }
        return f"https://vas-dom.bitrix24.ru/oauth/authorize/?{urlencode(params)}"

    @staticmethod
    def get_token(code):
        url = "https://vas-dom.bitrix24.ru/oauth/token/"
        data = {
            'grant_type': 'authorization_code',
            'client_id': BITRIX_CLIENT_ID,
            'client_secret': BITRIX_CLIENT_SECRET,
            'redirect_uri': BITRIX_REDIRECT_URI,
            'code': code
        }
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def refresh_token(refresh_token):
        url = "https://vas-dom.bitrix24.ru/oauth/token/"
        data = {
            'grant_type': 'refresh_token',
            'client_id': BITRIX_CLIENT_ID,
            'client_secret': BITRIX_CLIENT_SECRET,
            'refresh_token': refresh_token
        }
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def api_call(method, params=None):
        for attempt in range(3):
            try:
                token_data = BitrixAPI._get_valid_token()
                url = f"https://vas-dom.bitrix24.ru/rest/1/{method}"
                headers = {'Authorization': f'Bearer {token_data["access_token"]}'}
                response = requests.post(
                    url,
                    json=params,
                    headers=headers,
                    auth=BASIC_AUTH,
                    timeout=15
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401 and attempt < 2:
                    BitrixAPI._refresh_token()
                    continue
                raise
        return None

    @staticmethod
    def _get_valid_token():
        with sqlite3.connect('app.db') as conn:
            row = conn.execute('''
                SELECT access_token, refresh_token, expires_at 
                FROM bitrix_tokens 
                ORDER BY id DESC 
                LIMIT 1
            ''').fetchone()

            if row and datetime.fromisoformat(row[2]) > datetime.now():
                return {'access_token': row[0], 'refresh_token': row[1]}

            new_token = BitrixAPI.refresh_token(row[1])
            expires_at = datetime.now() + timedelta(seconds=new_token['expires_in'] - 60)
            conn.execute('''
                INSERT INTO bitrix_tokens (access_token, refresh_token, expires_at)
                VALUES (?, ?, ?)
            ''', (new_token['access_token'], new_token['refresh_token'], expires_at.isoformat()))
            return new_token

def async_task(func):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
    return wrapper

@app.route('/oauth/callback')
def oauth_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "Authorization code missing"}), 400

    try:
        token_data = BitrixAPI.get_token(code)
        expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'] - 60)
        
        with sqlite3.connect('app.db') as conn:
            conn.execute('''
                INSERT INTO bitrix_tokens (access_token, refresh_token, expires_at)
                VALUES (?, ?, ?)
            ''', (token_data['access_token'], token_data['refresh_token'], expires_at.isoformat()))
        
        return jsonify({"status": "success", "expires_at": expires_at.isoformat()})
    except Exception as e:
        logger.error(f"OAuth error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/webhook/disk', methods=['POST'])
@async_task
def handle_disk_webhook():
    try:
        raw_data = request.data.decode('utf-8')
        data = json.loads(re.sub(r'//.*|/\*.*?\*/|\{=[^}]+\}', '', raw_data, flags=re.DOTALL))
        
        if not all(key in data for key in ['folder_id', 'deal_id', 'file_ids']):
            logger.error("Invalid webhook data structure")
            return

        process_files(data['folder_id'], data['deal_id'], data['file_ids'])
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")

def process_files(folder_id, deal_id, file_ids):
    try:
        files = []
        for file_id in file_ids:
            file_info = BitrixAPI.api_call('disk.file.get', {'id': file_id})
            if file_info and 'DETAIL_URL' in file_info.get('result', {}):
                files.append({
                    'file_id': file_id,
                    'url': file_info['result']['DETAIL_URL'],
                    'name': file_info['result']['NAME']
                })

        if files:
            result = BitrixAPI.api_call('crm.deal.update', {
                'id': deal_id,
                'fields': {
                    FILE_FIELD_ID: [{'fileId': f['file_id']} for f in files]
                }
            })
            
            if result and 'result' in result:
                logger.info(f"Successfully attached {len(files)} files to deal {deal_id}")
            else:
                logger.error(f"Failed to attach files to deal {deal_id}")
    except Exception as e:
        logger.error(f"File processing error: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)), threaded=True)
