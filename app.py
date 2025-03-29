import os
import re
import json
import logging
from flask import Flask, request, jsonify
from requests.auth import HTTPBasicAuth
import requests
from datetime import datetime

app = Flask(__name__)

# Конфигурация
BITRIX_WEBHOOK_URL = "https://vas-dom.bitrix24.ru/rest/1/gq2ixv9nypiimwi9/"
BASIC_AUTH = HTTPBasicAuth("maslovmaksim92@yandex.ru", "123456")
FILE_FIELD_ID = "UF_CRM_1740994275251"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bitrix_integration.log')
    ]
)
logger = logging.getLogger(__name__)

def clean_and_parse_json(json_str):
    """Очистка JSON от комментариев и замена шаблонных переменных"""
    try:
        # Удаление комментариев
        json_str = re.sub(r'//.*', '', json_str)  # Однострочные
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)  # Многострочные
        
        # Замена шаблонных переменных на null
        json_str = re.sub(r'\{=[^}]+\}', 'null', json_str)
        
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        raise ValueError("Invalid JSON format")

@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    try:
        logger.info("="*50)
        logger.info(f"Incoming request at {datetime.now().isoformat()}")
        
        # Проверка Content-Type
        if request.content_type != 'application/json':
            logger.error("Invalid Content-Type")
            return jsonify({"error": "Content-Type must be application/json"}), 400

        # Обработка JSON
        try:
            raw_data = request.data.decode('utf-8')
            logger.debug(f"Raw request: {raw_data}")
            data = clean_and_parse_json(raw_data)
        except ValueError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            return jsonify({"error": str(e)}), 400

        # Валидация полей
        required_fields = ['folder_id', 'deal_id']
        if not all(field in data for field in required_fields):
            logger.error("Missing required fields")
            return jsonify({"error": "Missing folder_id or deal_id"}), 400

        folder_id = data['folder_id']
        deal_id = data['deal_id']
        
        logger.info(f"Processing deal {deal_id}, folder {folder_id}")

        # Здесь должна быть ваша основная логика обработки файлов
        # Временный ответ для тестирования
        response = {
            "status": "success",
            "data": {
                "folder_id": folder_id,
                "deal_id": deal_id
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Response: {json.dumps(response, indent=2)}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
