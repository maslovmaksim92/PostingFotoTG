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
FILE_FIELD_ID = "UF_CRM_1740994275251"  # Поле для прикрепления файлов

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    try:
        # 1. Проверка входящих данных
        data = request.get_json()
        if not data or "folder_id" not in data or "deal_id" not in data:
            logging.error("Неверный формат данных")
            return jsonify({"error": "Invalid data format"}), 400

        folder_id = data["folder_id"]
        deal_id = data["deal_id"]
        logging.info(f"Обработка deal_id: {deal_id}, folder_id: {folder_id}")

        # 2. Получаем список файлов из папки
        files_response = requests.post(
            f"{BITRIX_API_URL}disk.folder.getchildren",
            json={"id": folder_id},
            auth=BASIC_AUTH,
            timeout=10
        )
        
        if files_response.status_code != 200:
            logging.error(f"Ошибка API: {files_response.text}")
            return jsonify({"error": "API request failed"}), 500

        files = files_response.json().get("result", [])
        logging.info(f"Найдено {len(files)} файлов в папке")

        # 3. Обрабатываем каждый файл
        attached_files = []
        for file_info in files:
            if file_info.get("TYPE") != "file":
                continue

            try:
                # Скачиваем файл
                download_url = file_info["DOWNLOAD_URL"]
                file_content = requests.get(
                    download_url,
                    auth=BASIC_AUTH,
                    timeout=30
                ).content

                # Загружаем в хранилище
                upload_response = requests.post(
                    f"{BITRIX_API_URL}disk.storage.uploadfile",
                    files={
                        "fileContent": (file_info["NAME"], file_content)
                    },
                    auth=BASIC_AUTH,
                    timeout=30
                )

                if upload_response.status_code == 200:
                    file_id = upload_response.json().get("result", {}).get("ID")
                    if file_id:
                        attached_files.append(file_id)
                        logging.info(f"Файл {file_info['NAME']} успешно загружен (ID: {file_id})")
                else:
                    logging.warning(f"Ошибка загрузки файла {file_info['NAME']}")

            except Exception as e:
                logging.error(f"Ошибка обработки файла: {str(e)}")
                continue

        # 4. Прикрепляем файлы к сделке
        if attached_files:
            update_response = requests.post(
                f"{BITRIX_API_URL}crm.deal.update",
                json={
                    "id": deal_id,
                    "fields": {
                        FILE_FIELD_ID: attached_files
                    }
                },
                auth=BASIC_AUTH,
                timeout=10
            )

            if update_response.status_code == 200:
                logging.info(f"Успешно прикреплено {len(attached_files)} файлов к сделке {deal_id}")
                return jsonify({
                    "status": "success",
                    "files_attached": len(attached_files)
                })
            else:
                logging.error(f"Ошибка прикрепления файлов: {update_response.text}")

        return jsonify({"error": "No files processed"}), 400

    except Exception as e:
        logging.exception("Critical error in webhook handler")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
