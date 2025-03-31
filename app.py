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
DATABASE = os.getenv('DATABASE_URL', 'sqlite:///logs/app.db').replace('sqlite:///', '')

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
            logger.info(f"🔄 Запрос к {url} | Данные: {data}")
            response = requests.post(url, data=data, timeout=10)
            logger.info(f"📩 Ответ: {response.status_code} - {response.text}")
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

    @classmethod
    def get_valid_token(cls):
        with sqlite3.connect(DATABASE) as conn:
            row = conn.execute('SELECT access_token, refresh_token, expires_at FROM bitrix_tokens').fetchone()
            if row and datetime.fromisoformat(row[2]) > datetime.now():
                logger.info("🔐 Используется access_token из БД")
                return {'access_token': row[0], 'refresh_token': row[1]}
            if row:
                logger.info("♻️ Обновление access_token через refresh_token")
                new_token = cls.refresh_token(row[1])
                expires_at = datetime.now() + timedelta(seconds=new_token['expires_in'] - 60)
                conn.execute('DELETE FROM bitrix_tokens')
                conn.execute('INSERT INTO bitrix_tokens VALUES (?, ?, ?)',
                             (new_token['access_token'], new_token['refresh_token'], expires_at.isoformat()))
                conn.commit()
                logger.info("✅ Новый токен сохранён")
                return new_token
            logger.error("❌ Токены отсутствуют в базе данных")
            raise ValueError("Отсутствуют токены в базе данных")

    @classmethod
    def api_call(cls, method, params=None):
        token = cls.get_valid_token()
        headers = {'Authorization': f'Bearer {token["access_token"]}', 'Content-Type': 'application/json'}
        url = f"https://vas-dom.bitrix24.ru/rest/{method}"
        logger.info(f"📡 Bitrix API call: {url} | params: {params}")
        response = requests.post(url, json=params, headers=headers)
        logger.info(f"📨 API response: {response.status_code} | {response.text}")
        response.raise_for_status()
        return response.json()

# ======================= HELPER ============================
def transform_bitrix_data(data):
    if isinstance(data, dict):
        return {k: transform_bitrix_data(v) for k, v in data.items()}
    elif isinstance(data, str) and data.startswith("{=") and data.endswith("}"):
        inner = data[2:-1]
        parts = inner.split(".")
        last = parts[-1]
        if last.isdigit():
            return int(last)
        logger.info(f"🔁 Шаблон '{data}' -> '{last}'")
        return last
    return data

# ======================== ROUTES =============================
@app.route('/')
def health():
    return jsonify({"status": "ok", "ts": datetime.now().isoformat()}), 200

@app.route('/oauth/callback')
def oauth_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "No code"}), 400
    token_data = BitrixAPI.get_token(code)
    expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'] - 60)
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('DELETE FROM bitrix_tokens')
        conn.execute('INSERT INTO bitrix_tokens VALUES (?, ?, ?)',
                     (token_data['access_token'], token_data['refresh_token'], expires_at.isoformat()))
        conn.commit()
    logger.info("✅ Авторизация прошла успешно")
    return jsonify({"status": "Authorization successful"}), 200

@app.route('/webhook/disk', methods=['POST'])
def handle_disk_webhook():
    try:
        raw_data = request.data.decode('utf-8')
        logger.info(f"📥 Raw data: {raw_data}")
        data = json.loads(raw_data)
        transformed = transform_bitrix_data(data)
        logger.info(f"🧾 Преобразованные данные: {transformed}")

        deal_id = transformed.get("deal_id")
        if not deal_id or not str(deal_id).isdigit():
            logger.error(f"❌ Неверный deal_id: {deal_id}")
            return jsonify({"error": "Invalid deal_id"}), 400

        deal = BitrixAPI.api_call("crm.deal.get", {"id": int(deal_id)})
        folder_id = deal["result"].get(FOLDER_FIELD_ID)
        if not folder_id:
            return jsonify({"error": "folder_id not found in deal"}), 400

        folder_data = BitrixAPI.api_call("disk.folder.getchildren", {"id": folder_id})
        file_ids = [item["ID"] for item in folder_data.get("result", []) if item["TYPE"] == "file"]
        if not file_ids:
            return jsonify({"error": "No files found"}), 400

        threading.Thread(target=process_files, args=(folder_id, deal_id, file_ids), daemon=True).start()
        return jsonify({"status": "processing_started", "files": file_ids}), 202

    except Exception as e:
        logger.exception(f"🔥 Ошибка в handle_disk_webhook: {e}")
        return jsonify({"error": "Internal error"}), 500

# ======================== FILES =============================
def process_files(folder_id, deal_id, file_ids):
    try:
        files = []
        for fid in file_ids:
            file_info = BitrixAPI.api_call("disk.file.get", {"id": fid})
            if file_info.get("result"):
                files.append({"fileId": fid})
        if not files:
            logger.warning(f"⚠️ Нет файлов для обновления сделки {deal_id}")
            return
        update = BitrixAPI.api_call("crm.deal.update", {
            "id": int(deal_id),
            "fields": {FILE_FIELD_ID: files}
        })
        logger.info(f"✅ Сделка {deal_id} обновлена с {len(files)} файлами")
    except Exception as e:
        logger.exception(f"🔥 Ошибка в process_files: {e}")

# ======================== RUN =============================
@app.route("/log")
def show_log():
    try:
        with open("logs/app.log", "r", encoding="utf-8") as f:
            log_data = f.read()
        return f"<pre>{log_data}</pre>"
    except Exception as e:
        return f"Ошибка при чтении лога: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)), threaded=True)
