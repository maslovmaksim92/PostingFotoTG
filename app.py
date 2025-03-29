import os
import logging
from flask import Flask, request, jsonify
from requests.auth import HTTPBasicAuth
import requests
from urllib.parse import urlparse

app = Flask(__name__)

# Конфигурация (ЗАМЕНИТЕ на свои реальные значения!)
BITRIX_WEBHOOK_URL = "https://vas-dom.bitrix24.ru/rest/1/gq2ixv9nypiimwi9/"  # Ваш вебхук
BASIC_AUTH = HTTPBasicAuth("maslovmaksim92@yandex.ru", "123456")  # Данные для доступа к файлам
FILE_FIELD_ID = "UF_CRM_1740994275251"  # Поле для файлов в сделке

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    try:
        # 1. Проверка входящих данных
        data = request.get_json()
        if not data or "folder_id" not in data or "deal_id" not in data:
            return jsonify({"error": "Требуются folder_id и deal_id"}), 400

        folder_id = data["folder_id"]
        deal_id = data["deal_id"]
        logging.info(f"Обработка: сделка {deal_id}, папка {folder_id}")

        # 2. Получаем список файлов из папки (ИСПРАВЛЕННЫЙ МЕТОД)
        files_response = requests.get(
            f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren",
            params={"id": folder_id},  # Используем params вместо json
            auth=BASIC_AUTH
        )
        
        if files_response.status_code != 200:
            logging.error(f"Ошибка API: {files_response.text}")
            return jsonify({"error": "Ошибка при получении файлов"}), 500

        files = files_response.json().get("result", [])
        logging.info(f"Найдено файлов: {len(files)}")

        # 3. Обрабатываем каждый файл
        attached_files = []
        domain = urlparse(BITRIX_WEBHOOK_URL).netloc

        for file_info in files:
            if file_info.get("TYPE") != "file":
                continue

            try:
                # Скачивание файла
                file_url = f"https://{domain}{file_info['DOWNLOAD_URL']}"
                file_content = requests.get(file_url, auth=BASIC_AUTH).content

                # Загрузка в Bitrix24 (ИСПРАВЛЕННЫЙ МЕТОД)
                upload_response = requests.post(
                    f"{BITRIX_WEBHOOK_URL}disk.storage.uploadfile",
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
                        logging.info(f"Файл {file_info['NAME']} загружен (ID: {file_id})")

            except Exception as e:
                logging.error(f"Ошибка файла {file_info['NAME']}: {str(e)}")
                continue

        # 4. Прикрепляем файлы к сделке
        if attached_files:
            update_response = requests.post(
                f"{BITRIX_WEBHOOK_URL}crm.deal.update",
                json={
                    "id": deal_id,
                    "fields": {FILE_FIELD_ID: attached_files}
                },
                auth=BASIC_AUTH
            )

            if update_response.status_code == 200:
                return jsonify({
                    "status": "success",
                    "files_attached": len(attached_files)
                })

        return jsonify({"error": "Не удалось обработать файлы"}), 400

    except Exception as e:
        logging.exception("Ошибка в обработчике")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
