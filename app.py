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
FILE_FIELD_ID = "UF_CRM_1740994275251"
FOLDER_FIELD_ID = "UF_CRM_1743235503935"
STAGE_TO_TRACK = "УБОРКА СЕГОДНЯ"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "default_secret")  # Добавьте в .env

def validate_request(data):
    """Упрощенная проверка запросов от Bitrix24"""
    # Для вебхуков от бизнес-процессов проверяем наличие обязательных полей
    if 'event' in data or ('folder_id' in data and 'deal_id' in data):
        return True
    return False

@app.route("/", methods=["GET"])
def index():
    return "Сервис обработки файлов для Bitrix24", 200

@app.route("/webhook/stage", methods=["POST"])
def stage_webhook():
    """Обработчик для БП при смене стадии"""
    try:
        data = request.get_json()
        
        if not validate_request(data):
            logging.warning("Невалидный запрос")
            return jsonify({"error": "Invalid request"}), 400

        deal_id = data.get("data[FIELDS][ID]")
        if not deal_id:
            return jsonify({"error": "Deal ID missing"}), 400

        logging.info(f"Обработка сделки {deal_id}")
        
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
            logging.warning("Невалидный запрос на disk webhook")
            return jsonify({"error": "Invalid request"}), 400

        folder_id = data.get("folder_id")
        deal_id = data.get("deal_id")
        
        if not folder_id or not deal_id:
            return jsonify({"error": "Missing parameters"}), 400
        
        logging.info(f"Обработка файлов для сделки {deal_id}, папка {folder_id}")
        
        # Обрабатываем файлы в папке
        result = process_deal_files(deal_id, folder_id)
        
        if not result["status"]:
            return jsonify({"error": result.get("message", "File processing failed")}), 500

        return jsonify({
            "status": "success",
            "deal_id": deal_id,
            "files_processed": len(result["attached_files"])
        })

    except Exception as e:
        logging.exception("Disk Webhook Error")
        return jsonify({"error": str(e)}), 500

# ... [остальные вспомогательные функции остаются без изменений] ...

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
