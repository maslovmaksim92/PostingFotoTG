import os
import logging
from flask import Flask, request, jsonify
from requests.auth import HTTPBasicAuth
import requests
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import traceback

app = Flask(__name__)

# ========== КОНФИГУРАЦИЯ ==========
BITRIX_WEBHOOK_URL = "https://vas-dom.bitrix24.ru/rest/1/gq2ixv9nypiimwi9/"
BASIC_AUTH = HTTPBasicAuth("maslovmaksim92@yandex.ru", "123456")
FILE_FIELD_ID = "UF_CRM_1740994275251"
SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'docx'}

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

# ========== ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ ==========
class BitrixAPI:
    @staticmethod
    def log_api_call(method: str, url: str, params: dict = None):
        """Логирование вызовов API"""
        logger.debug(f"API Call: {method} {url}")
        if params:
            logger.debug(f"Params: {params}")

    @staticmethod
    def get_folder_files(folder_id: str) -> Tuple[List[Dict], Optional[str]]:
        """Получение списка файлов из папки с обработкой ошибок"""
        try:
            url = f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren"
            params = {'id': folder_id}
            
            BitrixAPI.log_api_call("GET", url, params)
            
            response = requests.get(
                url,
                params=params,
                auth=BASIC_AUTH,
                timeout=15
            )
            response.raise_for_status()
            
            logger.info(f"Успешно получены файлы из папки {folder_id}")
            return response.json().get('result', []), None
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка получения файлов: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            return [], error_msg

    @staticmethod
    def upload_file(file_name: str, file_content: bytes) -> Tuple[Optional[str], Optional[str]]:
        """Безопасная загрузка файла с валидацией"""
        try:
            # Проверка расширения файла
            if not BitrixAPI.is_file_allowed(file_name):
                error = f"Недопустимый тип файла: {file_name}"
                logger.warning(error)
                return None, error

            # Проверка размера файла
            if len(file_content) > MAX_FILE_SIZE:
                error = f"Файл слишком большой: {len(file_content)} байт"
                logger.warning(error)
                return None, error

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
                timeout=30
            )
            response.raise_for_status()
            
            file_id = response.json().get('result', {}).get('ID')
            logger.info(f"Файл {file_name} успешно загружен (ID: {file_id})")
            return file_id, None
            
        except Exception as e:
            error_msg = f"Ошибка загрузки файла: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            return None, error_msg

    @staticmethod
    def attach_files_to_deal(deal_id: str, file_ids: List[str]) -> Tuple[bool, Optional[str]]:
        """Прикрепление файлов к сделке с обработкой ошибок"""
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
                timeout=15
            )
            response.raise_for_status()
            
            logger.info(f"Файлы успешно прикреплены к сделке {deal_id}")
            return True, None
            
        except Exception as e:
            error_msg = f"Ошибка прикрепления файлов: {str(e)}"
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
            return False, error_msg

    @staticmethod
    def is_file_allowed(filename: str) -> bool:
        """Проверка расширения файла"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========
def validate_request(request) -> Tuple[Optional[dict], Optional[str]]:
    """Полная валидация входящего запроса"""
    try:
        # Проверка секретного ключа
        if request.headers.get('X-Secret-Key') != SECRET_KEY:
            return None, "Неверный секретный ключ"

        data = request.get_json()
        if not data:
            return None, "Отсутствует тело запроса"

        # Валидация обязательных полей
        required_fields = ['folder_id', 'deal_id']
        for field in required_fields:
            if field not in data:
                return None, f"Отсутствует обязательное поле: {field}"

        # Проверка формата ID
        if not str(data['folder_id']).isdigit() or not str(data['deal_id']).isdigit():
            return None, "ID папки и сделки должны быть числовыми"

        return data, None

    except Exception as e:
        logger.error(f"Ошибка валидации запроса: {str(e)}")
        logger.debug(traceback.format_exc())
        return None, "Ошибка обработки запроса"

def process_file(file_info: Dict) -> Tuple[Optional[str], Optional[str]]:
    """Обработка одного файла"""
    try:
        file_url = file_info.get('DOWNLOAD_URL')
        file_name = file_info.get('NAME')
        
        if not file_url or not file_name:
            return None, "Отсутствует URL или имя файла"

        logger.info(f"Начало обработки файла: {file_name}")

        # Скачивание файла
        response = requests.get(file_url, auth=BASIC_AUTH, timeout=30)
        response.raise_for_status()
        
        # Загрузка в Bitrix
        file_id, error = BitrixAPI.upload_file(file_name, response.content)
        if error:
            return None, error
            
        return file_id, None

    except Exception as e:
        error_msg = f"Ошибка обработки файла: {str(e)}"
        logger.error(error_msg)
        logger.debug(traceback.format_exc())
        return None, error_msg

# ========== ВЕБХУК ==========
@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    """Основной обработчик вебхука"""
    logger.info("="*50)
    logger.info(f"Новый запрос | {datetime.now().isoformat()}")
    logger.info("="*50)

    # Валидация запроса
    data, error = validate_request(request)
    if error:
        logger.error(f"Ошибка валидации: {error}")
        return jsonify({"status": "error", "message": error}), 400

    folder_id = str(data['folder_id'])
    deal_id = str(data['deal_id'])
    
    logger.info(f"Обработка сделки {deal_id}, папка {folder_id}")

    # Получаем список файлов
    files, error = BitrixAPI.get_folder_files(folder_id)
    if error:
        return jsonify({"status": "error", "message": error}), 400

    if not files:
        logger.info("Нет файлов для обработки")
        return jsonify({"status": "success", "message": "No files found"})

    # Обработка файлов
    successful_files = []
    failed_files = []
    
    for file_info in files:
        if file_info.get('TYPE') != 'file':
            continue

        file_id, error = process_file(file_info)
        if file_id:
            successful_files.append(file_id)
        else:
            failed_files.append({
                "name": file_info.get('NAME'),
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
                "details": error
            }), 500

    # Формирование отчета
    result = {
        "status": "success",
        "statistics": {
            "total_files": len(files),
            "processed": len(successful_files),
            "failed": len(failed_files)
        },
        "processed_files": successful_files,
        "failed_files": failed_files
    }

    logger.info(f"Итоговый результат: {result}")
    return jsonify(result)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000,
        debug=True,
        threaded=True
    )
