import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse
import hashlib

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
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")
BASIC_AUTH_LOGIN = os.getenv("BASIC_AUTH_LOGIN")
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD")
FILE_FIELD_ID = "UF_CRM_1740994275251"  # Поле для файлов в сделке
FOLDER_FIELD_ID = "UF_CRM_1743235503935"  # Поле с ссылкой на папку
STAGE_TO_TRACK = "УБОРКА СЕГОДНЯ"

# 🔒 Безопасность
def validate_request(data):
    """Проверка подлинности запроса от Bitrix24"""
    if not data.get("auth"):
        logging.warning("Запрос без авторизационных данных")
        return False
    return True

@app.route("/", methods=["GET"])
def index():
    return "Сервис обработки файлов для Bitrix24", 200

@app.route("/webhook/stage", methods=["POST"])
def stage_webhook():
    """Обработчик для БП при смене стадии"""
    try:
        data = request.get_json()
        
        if not validate_request(data):
            return jsonify({"error": "Unauthorized"}), 401

        deal_id = data.get("data[FIELDS][ID]")
        if not deal_id:
            return jsonify({"error": "Deal ID missing"}), 400

        # 1. Получаем данные сделки
        deal_data = get_deal_data(deal_id)
        if not deal_data:
            return jsonify({"error": "Deal not found"}), 404
        
        # 2. Создаем папку (если не создана)
        folder_name = f"Уборка {deal_id} - {deal_data.get('TITLE', '')}"[:100]
        folder_id = create_folder(folder_name)
        
        if not folder_id:
            return jsonify({"error": "Failed to create folder"}), 500

        # 3. Обновляем поле с папкой в сделке
        if not update_deal_field(deal_id, FOLDER_FIELD_ID, folder_id):
            return jsonify({"error": "Failed to update deal"}), 500

        return jsonify({
            "status": "success",
            "deal_id": deal_id,
            "folder_id": folder_id
        })

    except Exception as e:
        logging.exception("Stage Webhook Error")
        return jsonify({"error": str(e)}), 500

@app.route("/webhook/disk", methods=["POST"])
def disk_webhook():
    """Обработчик для БП при изменении в Диске"""
    try:
        data = request.get_json()
        
        if not validate_request(data):
            return jsonify({"error": "Unauthorized"}), 401

        folder_id = data.get("folder_id")
        deal_id = data.get("deal_id")
        
        if not folder_id or not deal_id:
            return jsonify({"error": "Missing parameters"}), 400
        
        # Обрабатываем файлы в папке
        result = process_deal_files(deal_id, folder_id)
        
        if not result:
            return jsonify({"error": "File processing failed"}), 500

        return jsonify({
            "status": "success",
            "deal_id": deal_id,
            "files_processed": len(result["attached_files"])
        })

    except Exception as e:
        logging.exception("Disk Webhook Error")
        return jsonify({"error": str(e)}), 500

# 🛠️ Вспомогательные функции
def create_folder(folder_name):
    """Создает папку на Диске"""
    try:
        response = requests.post(
            f"{BITRIX_WEBHOOK_URL}disk.folder.add",
            json={
                "NAME": folder_name,
                "PARENT_ID": 0  # Корневая папка
            },
            timeout=10
        )
        return response.json().get("result", {}).get("ID")
    except Exception as e:
        logging.error(f"Folder Creation Error: {e}")
        return None

def process_deal_files(deal_id, folder_id):
    """Обработка файлов в папке"""
    try:
        files = get_files_from_folder(folder_id)
        if not files:
            return {"status": False, "message": "No files found"}

        attached_files = []
        for file_info in [f for f in files.get("result", []) if f.get("TYPE") == 2]:
            file_id = process_single_file(file_info)
            if file_id:
                attached_files.append(file_id)

        if not attached_files:
            return {"status": False, "message": "No files processed"}

        update_success = update_deal_field(deal_id, FILE_FIELD_ID, attached_files)
        
        return {
            "status": update_success,
            "attached_files": attached_files
        }

    except Exception as e:
        logging.error(f"File Processing Error: {e}")
        return {"status": False, "error": str(e)}

def get_files_from_folder(folder_id):
    """Получает список файлов из папки"""
    try:
        response = requests.post(
            f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren",
            json={"id": folder_id},
            timeout=10
        )
        return response.json()
    except Exception as e:
        logging.error(f"Get Files Error: {e}")
        return None

def process_single_file(file_info):
    """Обрабатывает один файл"""
    try:
        download_url = file_info.get("DOWNLOAD_URL")
        if not download_url:
            return None

        domain = urlparse(BITRIX_WEBHOOK_URL).netloc
        file_url = f"https://{domain}{download_url}"
        file_name = os.path.basename(urlparse(file_url).path)
        
        # Генерируем уникальное имя файла
        file_hash = hashlib.md5(file_name.encode()).hexdigest()[:8]
        unique_name = f"{file_hash}_{file_name}"
        
        file_content = download_file(file_url)
        if not file_content:
            return None

        response = requests.post(
            f"{BITRIX_WEBHOOK_URL}disk.storage.uploadfile",
            files={
                "id": (None, "3"),  # ID хранилища
                "fileContent": (unique_name, file_content)
            },
            timeout=30
        )
        return response.json().get("result", {}).get("ID")
    except Exception as e:
        logging.error(f"File Processing Error: {e}")
        return None

def download_file(url):
    """Скачивает файл с базовой авторизацией"""
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(BASIC_AUTH_LOGIN, BASIC_AUTH_PASSWORD),
            timeout=30
        )
        return response.content if response.status_code == 200 else None
    except Exception as e:
        logging.error(f"Download Error: {e}")
        return None

def update_deal_field(deal_id, field_code, value):
    """Обновляет поле сделки"""
    try:
        response = requests.post(
            f"{BITRIX_WEBHOOK_URL}crm.deal.update",
            json={
                "id": deal_id,
                "fields": {field_code: value}
            },
            timeout=10
        )
        return response.json().get("result", False)
    except Exception as e:
        logging.error(f"Update Deal Error: {e}")
        return False

def get_deal_data(deal_id):
    """Получает данные сделки"""
    try:
        response = requests.post(
            f"{BITRIX_WEBHOOK_URL}crm.deal.get",
            json={"id": deal_id},
            timeout=10
        )
        return response.json().get("result", {})
    except Exception as e:
        logging.error(f"Get Deal Error: {e}")
        return None

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
