import os
import logging
from flask import Flask, request, jsonify
from requests.auth import HTTPBasicAuth
import requests
from urllib.parse import urlparse

app = Flask(__name__)

# Конфигурация
BITRIX_WEBHOOK_URL = "https://vas-dom.bitrix24.ru/rest/1/gq2ixv9nypiimwi9/"
BASIC_AUTH = HTTPBasicAuth("maslovmaksim92@yandex.ru", "123456")
FILE_FIELD_ID = "UF_CRM_1740994275251"

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

def download_file(file_url: str) -> bytes:
    """Скачивание файла с авторизацией"""
    try:
        response = requests.get(file_url, auth=BASIC_AUTH, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logging.error(f"Ошибка скачивания файла: {str(e)}")
        raise

def upload_to_bitrix(file_name: str, file_content: bytes) -> str:
    """Загрузка файла в Bitrix24"""
    try:
        response = requests.post(
            f"{BITRIX_WEBHOOK_URL}disk.storage.uploadfile",
            files={
                'id': (None, '3'),  # ID хранилища
                'fileContent': (file_name, file_content)
            },
            auth=BASIC_AUTH,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get('result', {}).get('ID')
    except Exception as e:
        logging.error(f"Ошибка загрузки в Bitrix: {str(e)}")
        raise

@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    try:
        data = request.get_json()
        if not data or "folder_id" not in data or "deal_id" not in data:
            return jsonify({"error": "Неверные параметры запроса"}), 400

        folder_id = data["folder_id"]
        deal_id = data["deal_id"]
        logging.info(f"Начало обработки: сделка {deal_id}, папка {folder_id}")

        # Получаем список файлов
        files_response = requests.get(
            f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren",
            params={'id': folder_id},
            auth=BASIC_AUTH,
            timeout=10
        )
        files_response.raise_for_status()
        
        files = files_response.json().get('result', [])
        logging.debug(f"Получено {len(files)} файлов из папки")

        attached_files = []
        for file_info in files:
            if file_info.get('TYPE') != 'file':
                continue

            try:
                file_url = file_info['DOWNLOAD_URL']
                file_name = file_info['NAME']
                
                # Скачиваем и загружаем файл
                file_content = download_file(file_url)
                file_id = upload_to_bitrix(file_name, file_content)
                
                if file_id:
                    attached_files.append(file_id)
                    logging.info(f"Успешно обработан файл: {file_name} (ID: {file_id})")

            except Exception as e:
                logging.warning(f"Пропущен файл {file_info.get('NAME')}: {str(e)}")
                continue

        # Прикрепляем файлы к сделке
        if attached_files:
            response = requests.post(
                f"{BITRIX_WEBHOOK_URL}crm.deal.update",
                json={
                    'id': deal_id,
                    'fields': {FILE_FIELD_ID: attached_files}
                },
                auth=BASIC_AUTH,
                timeout=10
            )
            response.raise_for_status()
            
            logging.info(f"Успешно прикреплено {len(attached_files)} файлов к сделке {deal_id}")
            return jsonify({
                "status": "success",
                "files_attached": len(attached_files),
                "file_ids": attached_files
            })

        return jsonify({"error": "Нет файлов для обработки"}), 400

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка API Bitrix24: {str(e)}")
        return jsonify({"error": "Ошибка взаимодействия с Bitrix24"}), 502
    except Exception as e:
        logging.exception("Критическая ошибка обработки")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
