import os
import re
import json
import logging
from flask import Flask, request, jsonify, redirect
from requests.auth import HTTPBasicAuth
import requests
from datetime import datetime
from urllib.parse import urlencode
import sqlite3
from telegram import Bot, Update
from telegram.ext import Dispatcher

# Инициализация приложения Flask
app = Flask(__name__)

# Конфигурация из переменных окружения
BITRIX_CLIENT_ID = os.getenv('BITRIX_CLIENT_ID')
BITRIX_CLIENT_SECRET = os.getenv('BITRIX_CLIENT_SECRET')
BITRIX_REDIRECT_URI = os.getenv('BITRIX_REDIRECT_URI')
BASIC_AUTH = HTTPBasicAuth(os.getenv('BASIC_AUTH_LOGIN'), os.getenv('BASIC_AUTH_PASSWORD'))
FILE_FIELD_ID = os.getenv('FILE_FIELD_ID')
FOLDER_FIELD_ID = os.getenv('FOLDER_FIELD_ID')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Инициализация Telegram бота
telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)
dispatcher = Dispatcher(telegram_bot, None, use_context=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(os.getenv('DATABASE_URL').replace('sqlite:///', ''))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bitrix_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_in INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class BitrixAPI:
    @staticmethod
    def get_auth_url():
        """Генерация URL для OAuth авторизации"""
        params = {
            'client_id': BITRIX_CLIENT_ID,
            'redirect_uri': BITRIX_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'crm,tasks,calendar,im,disk'
        }
        return f"https://vas-dom.bitrix24.ru/oauth/authorize/?{urlencode(params)}"

    @staticmethod
    def get_token(code):
        """Получение токена доступа"""
        url = "https://vas-dom.bitrix24.ru/oauth/token/"
        data = {
            'grant_type': 'authorization_code',
            'client_id': BITRIX_CLIENT_ID,
            'client_secret': BITRIX_CLIENT_SECRET,
            'redirect_uri': BITRIX_REDIRECT_URI,
            'code': code
        }
        response = requests.post(url, data=data)
        return response.json()

    @staticmethod
    def api_call(method, params=None, auth_token=None):
        """Универсальный метод для вызовов API Bitrix24"""
        url = f"https://vas-dom.bitrix24.ru/rest/1/{method}"
        headers = {'Authorization': f'Bearer {auth_token}'} if auth_token else None
        response = requests.post(url, json=params, headers=headers, auth=BASIC_AUTH)
        return response.json()

@app.route('/oauth/callback')
def oauth_callback():
    """Обработка OAuth перенаправления"""
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "Authorization code not provided"}), 400

    try:
        token_data = BitrixAPI.get_token(code)
        conn = sqlite3.connect(os.getenv('DATABASE_URL').replace('sqlite:///', ''))
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bitrix_tokens (access_token, refresh_token, expires_in)
            VALUES (?, ?, ?)
        ''', (token_data['access_token'], token_data['refresh_token'], token_data['expires_in']))
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "message": "Authorization successful"})
    except Exception as e:
        logger.error(f"OAuth error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/webhook/disk', methods=['POST'])
def handle_disk_webhook():
    """Обработчик вебхука для работы с файлами"""
    try:
        # Очистка и парсинг JSON
        raw_data = request.data.decode('utf-8')
        clean_data = re.sub(r'//.*|/\*.*?\*/', '', raw_data, flags=re.DOTALL)
        clean_data = re.sub(r'\{=[^}]+\}', 'null', clean_data)
        data = json.loads(clean_data)

        # Валидация данных
        if not all(k in data for k in ['folder_id', 'deal_id']):
            return jsonify({"error": "Missing required fields"}), 400

        # Основная логика обработки
        folder_id = data['folder_id']
        deal_id = data['deal_id']

        # Здесь должна быть ваша логика работы с файлами
        # Пример: получение списка файлов из папки
        files = BitrixAPI.api_call(
            'disk.folder.getchildren',
            {'id': folder_id},
            auth_token=os.getenv('BITRIX_ACCESS_TOKEN')
        )

        return jsonify({
            "status": "success",
            "folder_id": folder_id,
            "deal_id": deal_id,
            "files": files.get('result', [])
        })

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    """Вебхук для Telegram бота"""
    update = Update.de_json(request.get_json(force=True), telegram_bot)
    dispatcher.process_update(update)
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('DEBUG', 'false').lower() == 'true')
