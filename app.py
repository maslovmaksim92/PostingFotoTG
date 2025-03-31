import os
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

# Конфигурация из .env
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

# ================= DB INIT ====================
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

# ================= UTILS ====================
def transform_bitrix_data(data):
    """Преобразует шаблон {=Document.ID} в ID"""
    if isinstance(data, dict):
        return {k: transform_bitrix_data(v) for k, v in data.items()}
    elif isinstance(data, str) and data.startswith('{=') and data.endswith('}'):
        inner = data[2:-1]
        if '.' in inner:
            last = inner.split('.')[-1]
            logger.info(f"🔁 Шаблон '{data}' -> '{last}'")
            return last
        logger.info(f"🔁 Шаблон без точки '{data}' -> '{inner}'")
        return inner
    return data

# =============== Bitrix API ===================
class BitrixAPI:

    @staticmethod
    def execute_request(url, data):
        try:
            logger.info(f"🌐 Отправка запроса: {url} | data={data}")
            response = requests.post(url, data=data, timeout=10)
            logger.info(f"📬 Ответ: {response.status_code} | {response.text}")
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
                logger.info("♻️ Токен устарел, обновляем...")
                new_token = cls.refresh_token(row[1])
                expires_at = datetime.now() + timedelta(seconds=new_token['expires_in'] - 60)
                conn.execute('DELETE FROM bitrix_tokens')
                conn.execute('INSERT INTO bitrix_tokens VALUES (?, ?, ?)',
                             (new_token['access_token'], new_token['refresh_token'], expires_at.isoformat()))
                conn.commit()
                logger.info("✅ Новый токен сохранен")
                return new_token
            logger.error("🚫 Токены отсутствуют в БД")
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

# ============== ENDPOINTS ==================
@app.route('/')
def health():
    return jsonify({"status": "ok", "ts": datetime.now().isoformat()}), 200

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
    logger.info("✅ Авторизация прошла")
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
        if not deal_id:
            return jsonify({"error": "Missing deal_id"}), 400

        # Получаем сделку
        deal = BitrixAPI.api_call("crm.deal.get", {"id": deal_id})
        folder_id = deal["result"].get(FOLDER_FIELD_ID)
        if not folder_id:
            logger.warning(f"⚠️ В сделке {deal_id} не найдено поле {FOLDER_FIELD_ID}")
            return jsonify({"error": "No folder_id"}), 400

        # Получаем список файлов в папке
        folder_data = BitrixAPI.api_call("disk.folder.getchildren", {"id": folder_id})
        file_ids = [item["ID"] for item in folder_data.get("result", []) if item["TYPE"] == "file"]
        logger.info(f"📂 Файлы в папке {folder_id}: {file_ids}")

        if not file_ids:
            return jsonify({"error": "No files found in folder"}), 400

        threading.Thread(target=process_files, args=(deal_id, file_ids), daemon=True).start()
        return jsonify({"status": "processing_started", "files": file_ids})

    except Exception as e:
        logger.exception(f"🔥 Ошибка в handle_disk_webhook: {e}")
        return jsonify({"error": "internal error"}), 500

def process_files(deal_id, file_ids):
    try:
        files = []
        for fid in file_ids:
            file_info = BitrixAPI.api_call("disk.file.get", {"id": fid})
            if file_info.get("result"):
                files.append({"fileId": fid})
                logger.info(f"📎 Файл добавлен: {file_info['result'].get('NAME')}")
        if not files:
            logger.warning("🚫 Нет валидных файлов для обновления")
            return
        update = {"id": deal_id, "fields": {FILE_FIELD_ID: files}}
        result = BitrixAPI.api_call("crm.deal.update", update)
        logger.info(f"✅ Обновление сделки {deal_id}: {json.dumps(result)}")
    except Exception as e:
        logger.exception(f"🔥 Ошибка в process_files: {e}")

# ============ MAIN =============
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)), debug=False)
