import os
import logging
from flask import Flask, request, jsonify
from requests.auth import HTTPBasicAuth
import requests
from urllib.parse import urlparse

app = Flask(__name__)

# Конфигурация
BITRIX_API_URL = "https://vas-dom.bitrix24.ru/rest/1/gq2ixv9nypiimwi9/"
BASIC_AUTH = HTTPBasicAuth("maslovmaksim92@yandex.ru", "123456")
FILE_FIELD_ID = "UF_CRM_1740994275251"

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    try:
        data = request.get_json()
        if not data or "folder_id" not in data or "deal_id" not in data:
            return jsonify({"error": "Требуются folder_id и deal_id"}), 400

        folder_id = data["folder_id"]
        deal_id = data["deal_id"]
        logging.info(f"Обработка: сделка {deal_id}, папка {folder_id}")

        # 1. Получаем список файлов
        files_response = requests.get(
            f"{BITRIX_API_URL}disk.folder.getchildren",
            params={"id": folder_id},
            auth=BASIC_AUTH
        )
        
        if files_response.status_code != 200:
            error_msg = files_response.json().get("error_description", "Unknown error")
            logging.error(f"API Error: {error_msg}")
            return jsonify({"error": f"API Error: {error_msg}"}), 500

        files = files_response.json().get("result", [])
        if not files:
            return jsonify({"error": "Папка пуста"}), 404

        # 2. Обрабатываем файлы
        attached_files = []
        domain = urlparse(BITRIX_API_URL).netloc

        for file_info in files:
            if file_info.get("TYPE") != "file":
                continue

            try:
                # Скачивание
                file_url = file_info["DOWNLOAD_URL"]
                if not file_url.startswith("http"):
                    file_url = f"https://{domain}{file_url}"
                
                file_content = requests.get(file_url, auth=BASIC_AUTH).content

                # Загрузка
                upload_response = requests.post(
                    f"{BITRIX_API_URL}disk.storage.uploadfile",
                    files={
                        "id": (None, "3"),  # ID хранилища
                        "fileContent": (file_info["NAME"], file_content)
                    },
                    auth=BASIC_AUTH
                )

                if upload_response.status_code == 200:
                    file_id = upload_response.json().get("result", {}).get("ID")
                    if file_id:
                        attached_files.append(file_id)
                        logging.info(f"Успешно: {file_info['NAME']} -> ID {file_id}")

            except Exception as e:
                logging.error(f"Ошибка файла {file_info['NAME']}: {str(e)}")
                continue

        # 3. Прикрепляем к сделке
        if attached_files:
            update_response = requests.post(
                f"{BITRIX_API_URL}crm.deal.update",
                json={
                    "id": deal_id,
                    "fields": {FILE_FIELD_ID: attached_files}
                },
                auth=BASIC_AUTH
            )

            if update_response.status_code == 200:
                return jsonify({
                    "status": "success",
                    "files_attached": len(attached_files),
                    "file_ids": attached_files
                })

        return jsonify({"error": "Нет файлов для прикрепления"}), 400

    except Exception as e:
        logging.exception("Critical error")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
