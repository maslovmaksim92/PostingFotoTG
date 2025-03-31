import os
import sqlite3
import threading
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)

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
        conn.execute('''CREATE TABLE IF NOT EXISTS bitrix_tokens (
            access_token TEXT,
            refresh_token TEXT,
            expires_at TEXT
        )''')
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
            logger.error(f"🔥 Ошибка запроса: {e}")
            raise

    @staticmethod
    def get_token(code):
        return BitrixAPI.execute_request("https://oauth.bitrix.info/oauth/token/", {
            'grant_type': 'authorization_code',
            'client_id': BITRIX_CLIENT_ID,
            'client_secret': BITRIX_CLIENT_SECRET,
            'redirect_uri': BITRIX_REDIRECT_URI,
            'code': code
        })

    @staticmethod
    def refresh_token(refresh_token):
        return BitrixAPI.execute_request("https://oauth.bitrix.info/oauth/token/", {
            'grant_type': 'refresh_token',
            'client_id': BITRIX_CLIENT_ID,
            'client_secret': BITRIX_CLIENT_SECRET,
            'refresh_token': refresh_token
        })

    @staticmethod
    def get_valid_token():
        with sqlite3.connect(DATABASE) as conn:
            row = conn.execute("SELECT access_token, refresh_token, expires_at FROM bitrix_tokens ORDER BY ROWID DESC LIMIT 1").fetchone()
            if row:
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

            raise ValueError("Отсутствуют токены в базе данных")

    @staticmethod
    def api_call(method, params=None):
        token = BitrixAPI.get_valid_token()
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
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
    logger.info("✅ Авторизация прошла успешно")
    return jsonify({"status": "Authorization successful"}), 200

@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    try:
        raw_data = request.data.decode("utf-8")
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

        logger.info(f"🔁 Преобразованные данные: {{'folder_id': '{folder_id}', 'deal_id': '{deal_id}'}}")
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

@app.route("/log")
def show_log():
    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            return f.read(), 200
    except Exception as e:
        return f"Ошибка при чтении лога: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)), threaded=True)
