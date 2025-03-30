import os
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect
from dotenv import load_dotenv
import requests
from urllib.parse import urlencode

load_dotenv()

app = Flask(__name__)

# Переменные окружения
BITRIX_CLIENT_ID = os.getenv('BITRIX_CLIENT_ID')
BITRIX_CLIENT_SECRET = os.getenv('BITRIX_CLIENT_SECRET')
BITRIX_REDIRECT_URI = os.getenv('BITRIX_REDIRECT_URI')
BITRIX_WEBHOOK_URL = os.getenv('BITRIX_WEBHOOK_URL')
FILE_FIELD_ID = os.getenv('FILE_FIELD_ID')
FOLDER_FIELD_ID = os.getenv('FOLDER_FIELD_ID')

# Логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# База данных (SQLite)
DATABASE = os.getenv('DATABASE_URL', 'sqlite:///app.db').replace('sqlite:///', '')

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bitrix_tokens (
                access_token TEXT,
                refresh_token TEXT,
                expires_at TIMESTAMP
            )
        ''')

init_db()

class BitrixAPI:
    @staticmethod
    def get_token(code):
        response = requests.post("https://oauth.bitrix.info/oauth/token/", data={
            'grant_type': 'authorization_code',
            'client_id': BITRIX_CLIENT_ID,
            'client_secret': BITRIX_CLIENT_SECRET,
            'redirect_uri': BITRIX_REDIRECT_URI,
            'code': code
        })
        return response.json()

    @staticmethod
    def refresh_token(refresh_token):
        response = requests.post("https://oauth.bitrix.info/oauth/token/", data={
            'grant_type': 'refresh_token',
            'client_id': BITRIX_CLIENT_ID,
            'client_secret': BITRIX_CLIENT_SECRET,
            'refresh_token': refresh_token
        })
        return response.json()

    @staticmethod
    def call(method, params):
        token_data = BitrixAPI.get_valid_token()
        url = f"https://vas-dom.bitrix24.ru/rest/{token_data['access_token']}/{method}"
        response = requests.post(url, json=params)
        return response.json()

    @staticmethod
    def get_valid_token():
        with sqlite3.connect(DATABASE) as conn:
            row = conn.execute('SELECT access_token, refresh_token, expires_at FROM bitrix_tokens').fetchone()
            if row and datetime.fromisoformat(row[2]) > datetime.now():
                return {'access_token': row[0], 'refresh_token': row[1]}
            if row:
                new_token = BitrixAPI.refresh_token(row[1])
                expires_at = datetime.now() + timedelta(seconds=new_token['expires_in'] - 60)
                conn.execute('DELETE FROM bitrix_tokens')
                conn.execute('INSERT INTO bitrix_tokens VALUES (?, ?, ?)', (
                    new_token['access_token'],
                    new_token['refresh_token'],
                    expires_at.isoformat()
                ))
                return new_token
            raise Exception("Токен отсутствует!")

@app.route('/')
def index():
    return "Сервис активен ✅"

@app.route('/oauth/callback')
def oauth_callback():
    code = request.args.get('code')
    token_data = BitrixAPI.get_token(code)
    expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'] - 60)
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('DELETE FROM bitrix_tokens')
        conn.execute('INSERT INTO bitrix_tokens VALUES (?, ?, ?)', (
            token_data['access_token'],
            token_data['refresh_token'],
            expires_at.isoformat()
        ))
    return jsonify({"status": "Авторизация успешна!"})

@app.route('/webhook/disk', methods=['POST'])
def webhook_disk():
    data = request.json
    folder_id = data.get('folder_id')
    deal_id = data.get('deal_id')

    threading.Thread(target=attach_files, args=(folder_id, deal_id)).start()
    return jsonify({"status": "Процесс запущен."})

def attach_files(folder_id, deal_id):
    files_resp = BitrixAPI.call('disk.folder.getchildren', {'id': folder_id})
    file_ids = [int(f['ID']) for f in files_resp['result'] if f['TYPE'] == 2]

    if not file_ids:
        logging.info("Файлы не найдены.")
        return

    BitrixAPI.call('crm.deal.update', {
        'id': deal_id,
        'fields': {FILE_FIELD_ID: file_ids}
    })
    logging.info(f"Файлы прикреплены к сделке {deal_id}.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
