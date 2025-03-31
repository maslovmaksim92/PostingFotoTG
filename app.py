import os
import re
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect
from dotenv import load_dotenv
import requests

load_dotenv()

# === Логирование: и в консоль, и в файл ===
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

log_file_path = os.path.join(log_dir, "app.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file_path, encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфигурация
BITRIX_CLIENT_ID = os.getenv('BITRIX_CLIENT_ID')
BITRIX_CLIENT_SECRET = os.getenv('BITRIX_CLIENT_SECRET')
BITRIX_REDIRECT_URI = os.getenv('BITRIX_REDIRECT_URI')
FILE_FIELD_ID = os.getenv('FILE_FIELD_ID')
FOLDER_FIELD_ID = os.getenv('FOLDER_FIELD_ID')
DATABASE = os.getenv('DATABASE_URL', 'sqlite:///logs/app.db').replace('sqlite:///', '')

# ======================= DB ============================
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

# ====================== BITRIX API ============================
class BitrixAPI:
    @staticmethod
    def execute_request(url, data):
        try:
            logger.info(f"Запрос к {url} | Данные: {data}")
            response = requests.post(url, data=data, timeout=10)
            logger.info(f"Ответ: {response.status_code} - {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"❌ Ошибка запроса: {str(e)}")
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

# ======================= TOKENS ============================
def get_valid_token():
    with sqlite3.connect(DATABASE) as conn:
        row = conn.execute("SELECT access_token, refresh_token, expires_at FROM bitrix_tokens ORDER BY ROWID DESC LIMIT 1").fetchone()
        if not row:
            raise ValueError("Отсутствуют токены в базе данных")

        access_token, refresh_token, expires_at = row
        if datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S") <= datetime.utcnow():
            logger.info("🔄 Токен просрочен. Обновление...")
            new_data = BitrixAPI.refresh_token(refresh_token)
            access_token = new_data['access_token']
            refresh_token = new_data['refresh_token']
            expires_in = new_data['expires_in']
            expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).strftime("%Y-%m-%d %H:%M:%S")

            conn.execute("DELETE FROM bitrix_tokens")
            conn.execute("INSERT INTO bitrix_tokens VALUES (?, ?, ?)", (access_token, refresh_token, expires_at))
            conn.commit()

        return access_token

# ======================= ROUTES ============================
@app.route("/auth/bitrix")
def auth():
    url = f"https://oauth.bitrix.info/oauth/authorize/?client_id={BITRIX_CLIENT_ID}&response_type=code&redirect_uri={BITRIX_REDIRECT_URI}"
    return redirect(url)

@app.route("/oauth/callback")
def oauth_callback():
    code = request.args.get("code")
    if not code:
        return "❌ Не передан код авторизации", 400

    data = BitrixAPI.get_token(code)
    access_token = data['access_token']
    refresh_token = data['refresh_token']
    expires_in = data['expires_in']
    expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(DATABASE) as conn:
        conn.execute("DELETE FROM bitrix_tokens")
        conn.execute("INSERT INTO bitrix_tokens VALUES (?, ?, ?)", (access_token, refresh_token, expires_at))
        conn.commit()

    return "✅ Авторизация прошла успешно"

@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    try:
        raw_data = request.data.decode("utf-8")
        logger.info(f"📥 Raw data: {raw_data}")
        data = json.loads(raw_data)

        folder_id = data.get("folder_id")
        deal_id = data.get("deal_id")

        logger.info(f"🔁 Преобразованные данные: {{'folder_id': '{folder_id}', 'deal_id': '{deal_id}'}}")

        if not deal_id or not deal_id.isdigit():
            logger.error(f"❌ Неверный deal_id: {deal_id}")
            return jsonify({"error": "Invalid deal_id"}), 400

        token = get_valid_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://{request.host}/rest/crm.deal.get.json?id={deal_id}"

        logger.info(f"📡 Проверка сделки {deal_id} через API...")
        response = requests.get(url, headers=headers)
        logger.info(f"✅ Ответ: {response.text}")
        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error(f"🔥 Ошибка в handle_disk_webhook: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/log")
def show_log():
    try:
        with open("logs/app.log", "r", encoding="utf-8") as f:
            log_data = f.read()
        return f"<pre>{log_data}</pre>"
    except Exception as e:
        return f"Ошибка при чтении лога: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
