import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse

# Настройка логов
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler = logging.FileHandler(os.path.join(LOG_DIR, "app.log"), encoding="utf-8")
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])

app = Flask(__name__)
load_dotenv()

# Конфигурация
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "").strip()
BASIC_AUTH_LOGIN = os.getenv("BASIC_AUTH_LOGIN", "").strip()
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "").strip()
FILE_FIELD_ID = os.getenv("FILE_FIELD_ID", "UF_CRM_1740994275251")
FOLDER_FIELD_ID = os.getenv("FOLDER_FIELD_ID", "UF_CRM_1743235503935")
STAGE_TO_TRACK = "УБОРКА СЕГОДНЯ"

# OAuth
BITRIX_CLIENT_ID = os.getenv("BITRIX_CLIENT_ID").replace("local.", "local:")  # Исправление формата
BITRIX_CLIENT_SECRET = os.getenv("BITRIX_CLIENT_SECRET")
BITRIX_REDIRECT_URI = os.getenv("BITRIX_REDIRECT_URI")

# Глобальная переменная для токена (временное решение)
ACCESS_TOKEN = None

@app.route("/", methods=["GET"])
def index():
    return "Сервис обработки файлов для Bitrix24", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    """Обработчик вебхука от Bitrix24"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Empty request"}), 400

        event = data.get("event")
        deal_id = data.get("data[FIELDS][ID]")
        deal_stage = data.get("data[FIELDS][STAGE_ID]")

        if event != "ONCRMDEALUPDATE" or not deal_id:
            return jsonify({"status": "ignored"}), 200

        if deal_stage.upper() == STAGE_TO_TRACK.upper():
            process_deal_files(deal_id)
        
        return jsonify({"status": "processed"}), 200

    except Exception as e:
        logging.exception("Ошибка в обработчике вебхука")
        return jsonify({"error": str(e)}), 500

@app.route("/oauth/callback")
def oauth_callback():
    global ACCESS_TOKEN
    auth_code = request.args.get("code")
    if not auth_code:
        return jsonify({"error": "Authorization code missing"}), 400

    try:
        token_url = "https://oauth.bitrix.info/oauth/token/"
        payload = {
            "grant_type": "authorization_code",
            "client_id": BITRIX_CLIENT_ID,
            "client_secret": BITRIX_CLIENT_SECRET,
            "code": auth_code,
            "redirect_uri": BITRIX_REDIRECT_URI
        }
        response = requests.post(token_url, data=payload, timeout=10)
        if response.status_code != 200:
            logging.error(f"Ошибка получения токена: {response.text}")
            return jsonify({"error": "Token exchange failed"}), 400

        token_data = response.json()
        ACCESS_TOKEN = token_data.get("access_token")
        logging.info("✅ Успешная авторизация")
        return jsonify({"status": "success", "access_token": ACCESS_TOKEN})

    except Exception as e:
        logging.exception("Ошибка в OAuth callback")
        return jsonify({"error": str(e)}), 500

def process_deal_files(deal_id):
    """Основная логика обработки файлов"""
    try:
        deal_data = get_deal_data(deal_id)
        if not deal_data:
            return False

        folder_id = deal_data.get(FOLDER_FIELD_ID)
        if not folder_id:
            logging.error(f"Для сделки {deal_id} не указана папка")
            return False

        files = get_files_from_folder(folder_id)
        if not files:
            logging.info(f"В папке {folder_id} нет файлов")
            return False

        attached_files = []
        for file_info in files:
            file_id = process_single_file(file_info)
            if file_id:
                attached_files.append(file_id)

        if attached_files:
            return update_deal_files(deal_id, attached_files)
        
        return False

    except Exception as e:
        logging.exception(f"Ошибка обработки файлов сделки {deal_id}")
        return False

def get_folder_id_by_path(path: str):
    """Получение folder_id по пути через OAuth"""
    try:
        response = requests.post(
            f"{BITRIX_WEBHOOK_URL}disk.folder.getbypath",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            json={"path": path},
            timeout=10
        )
        return response.json().get("result", {}).get("ID")
    except Exception as e:
        logging.error(f"Ошибка получения folder_id: {e}")
        return None

# Остальные функции (get_deal_data, get_files_from_folder, download_file и т.д.) остаются без изменений

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
