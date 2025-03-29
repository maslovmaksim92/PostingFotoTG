import os
import logging
from flask import Flask, request, jsonify
from requests.auth import HTTPBasicAuth
import requests
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import traceback
import json

app = Flask(__name__)

# ========== КОНФИГУРАЦИЯ ==========
BITRIX_WEBHOOK_URL = "https://vas-dom.bitrix24.ru/rest/1/gq2ixv9nypiimwi9/"
BASIC_AUTH = HTTPBasicAuth("maslovmaksim92@yandex.ru", "123456")
FILE_FIELD_ID = "UF_CRM_1740994275251"

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
def setup_logging():
    """Конфигурация детализированного логирования"""
    log_format = '%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d - %(message)s'
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            logging.FileHandler('bitrix_integration.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.getLogger('requests').setLevel(logging.WARNING)

setup_logging()
logger = logging.getLogger(__name__)

class BitrixAPI:
    @staticmethod
    def log_api_call(method: str, url: str, params: dict = None):
        """Логирование вызовов API"""
        logger.debug(f"API Call: {method} {url}")
        if params:
            logger.debug(f"Params: {params}")

    @staticmethod
    def get_folder_files(folder_id: str) -> Tuple[List[Dict], Optional[str]]:
        """Получение списка файлов из папки"""
        try:
            url = f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren"
            params = {'id': folder_id}
            
            BitrixAPI.log_api_call("GET", url, params)
            
            response = requests.get(
                url,
                params=params,
                auth=BASIC_AUTH,
                timeout=30
            )
            response.raise_for_status()
            
            files = response.json().get('result', [])
            logger.info(f"Успешно получено {len(files)} файлов из папки {folder_id}")
            return files, None
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка получения файлов: {str(e)}"
            if hasattr(e, 'response'):
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            logger.error(traceback.format_exc())
            return [], error_msg

    @staticmethod
    def upload_file(file_name: str, file_content: bytes) -> Tuple[Optional[str], Optional[str]]:
        """Загрузка файла в Bitrix24"""
        try:
            url = f"{BITRIX_WEBHOOK_URL}disk.storage.uploadfile"
            files = {
                'id': (None, '3'),
                'fileContent': (file_name, file_content)
            }
            
            BitrixAPI.log_api_call("POST", url)
            
            response = requests.post(
                url,
                files=files,
                auth=BASIC_AUTH,
                timeout=60
            )
            response.raise_for_status()
            
            file_id = response.json().get('result', {}).get('ID')
            logger.info(f"Файл {file_name} успешно загружен (ID: {file_id})")
            return file_id, None
            
        except Exception as e:
            error_msg = f"Ошибка загрузки файла: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return None, error_msg

    @staticmethod
    def attach_files_to_deal(deal_id: str, file_ids: List[str]) -> Tuple[bool, Optional[str]]:
        """Прикрепление файлов к сделке"""
        try:
            url = f"{BITRIX_WEBHOOK_URL}crm.deal.update"
            payload = {
                'id': deal_id,
                'fields': {FILE_FIELD_ID: file_ids}
            }
            
            BitrixAPI.log_api_call("POST", url, payload)
            
            response = requests.post(
                url,
                json=payload,
                auth=BASIC_AUTH,
                timeout=30
            )
            response.raise_for_status()
            
            logger.info(f"Успешно прикреплено {len(file_ids)} файлов к сделке {deal_id}")
            return True, None
            
        except Exception as e:
            error_msg = f"Ошибка прикрепления файлов: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return False, error_msg

def validate_and_parse_request(request) -> Tuple[Optional[dict], Optional[str]]:
    """Валидация и парсинг входящего запроса"""
    try:
        # Проверка наличия данных
        if not request.data:
            return None, "Пустое тело запроса"

        # Попытка парсинга JSON
        try:
            data = json.loads(request.data.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {str(e)}")
            logger.debug(f"Полученные сырые данные: {request.data.decode('utf-8', errors='replace')}")
            return None, f"Невалидный JSON: {str(e)}"

        # Проверка структуры данных
        if not isinstance(data, dict):
            return None, "Ожидается JSON объект"

        # Проверка обязательных полей
        required_fields = ['folder_id', 'deal_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return None, f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"

        # Проверка формата ID
        if not str(data['folder_id']).isdigit() or not str(data['deal_id']).isdigit():
            return None, "ID папки и сделки должны быть числовыми"

        return data, None

    except Exception as e:
        logger.error(f"Ошибка валидации запроса: {str(e)}")
        logger.error(traceback.format_exc())
        return None, "Ошибка обработки запроса"

@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    """Основной обработчик вебхука"""
    logger.info("="*80)
    logger.info(f"Начало обработки запроса | {datetime.now().isoformat()}")
    logger.info("-"*80)
    logger.debug(f"Headers: {dict(request.headers)}")
    logger.debug(f"Raw data: {request.data.decode('utf-8', errors='replace')}")

    # Валидация запроса
    data, error = validate_and_parse_request(request)
    if error:
        logger.error(f"Ошибка валидации: {error}")
        return jsonify({
            "status": "error",
            "message": error,
            "timestamp": datetime.now().isoformat()
        }), 400

    folder_id = str(data['folder_id'])
    deal_id = str(data['deal_id'])
    
    logger.info(f"Обработка: сделка {deal_id}, папка {folder_id}")

    # Получаем список файлов
    files, error = BitrixAPI.get_folder_files(folder_id)
    if error:
        return jsonify({
            "status": "error",
            "message": error,
            "timestamp": datetime.now().isoformat()
        }), 400

    if not files:
        logger.info("Нет файлов для обработки")
        return jsonify({
            "status": "success",
            "message": "No files found",
            "timestamp": datetime.now().isoformat()
        })

    # Обработка файлов
    successful_files = []
    failed_files = []
    
    for file_info in files:
        if file_info.get('TYPE') != 'file':
            continue

        file_name = file_info.get('NAME')
        file_url = file_info.get('DOWNLOAD_URL')
        
        logger.info(f"Обработка файла: {file_name}")

        file_id, error = BitrixAPI.upload_file(file_name, requests.get(file_url, auth=BASIC_AUTH, timeout=60).content)
        if file_id:
            successful_files.append(file_id)
        else:
            failed_files.append({
                "file_name": file_name,
                "error": error or "Unknown error"
            })

    # Прикрепление файлов к сделке
    if successful_files:
        success, error = BitrixAPI.attach_files_to_deal(deal_id, successful_files)
        if not success:
            logger.error(f"Ошибка прикрепления файлов: {error}")
            return jsonify({
                "status": "error",
                "message": "File attachment failed",
                "details": error,
                "timestamp": datetime.now().isoformat()
            }), 500

    # Формирование результата
    result = {
        "status": "success",
        "statistics": {
            "total_files": len(files),
            "processed": len(successful_files),
            "failed": len(failed_files)
        },
        "processed_files": successful_files,
        "failed_files": failed_files,
        "timestamp": datetime.now().isoformat()
    }

    logger.info("-"*80)
    logger.info("Результат обработки:")
    logger.info(json.dumps(result, indent=2, ensure_ascii=False))
    logger.info("="*80)
    
    return jsonify(result)

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"404 Not Found: {request.url}")
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "timestamp": datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 Internal Server Error: {str(error)}")
    logger.error(traceback.format_exc())
    return jsonify({
        "status": "error",
        "message": "Internal server error",
        "timestamp": datetime.now().isoformat()
    }), 500

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000,
        debug=False,
        threaded=True
    )
