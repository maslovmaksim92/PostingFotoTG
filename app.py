import os
import logging
from flask import Flask, request, jsonify
from requests.auth import HTTPBasicAuth
import requests
from urllib.parse import urlparse

app = Flask(__name__)

# Конфигурация (проверьте эти значения в .env)
BITRIX_API_URL = os.getenv("BITRIX_WEBHOOK_URL", "https://vas-dom.bitrix24.ru/rest/1/gq2ixv9nypiimwi9/")
BASIC_AUTH = HTTPBasicAuth(
    os.getenv("BASIC_AUTH_LOGIN", "maslovmaksim92@yandex.ru"),
    os.getenv("BASIC_AUTH_PASSWORD", "123456")
)
FILE_FIELD_ID = "UF_CRM_1740994275251"  # Поле для файлов из вашего скриншота

@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    try:
        # 1. Проверка данных
        data = request.get_json()
        if not data or "folder_id" not in data or "deal_id" not in data:
            return jsonify({"error": "Неверный формат данных"}), 400

        # 2. Получаем файлы из папки
        folder_id = data["folder_id"]
        files_response = requests.post(
            f"{BITRIX_API_URL}disk.folder.getchildren",
            json={"id": folder_id},
            auth=BASIC_AUTH,
            timeout=10
        )
        
        if files_response.status_code != 200:
            logging.error(f"Ошибка API Bitrix24: {files_response.text}")
            return jsonify({"error": "Ошибка API Bitrix24"}), 500

        files = [f for f in files_response.json().get("result", []) 
                if f.get("TYPE") == 2]  # TYPE=2 - файлы

        # 3. Обработка файлов
        attached_files = []
        domain = urlparse(BITRIX_API_URL).netloc
        
        for file_info in files:
            try:
                # Скачивание
                file_url = f"https://{domain}{file_info['DOWNLOAD_URL']}"
                file_content = requests.get(
                    file_url, 
                    auth=BASIC_AUTH,
                    timeout=30
                ).content
                
                # Загрузка
                upload_response = requests.post(
                    f"{BITRIX_API_URL}disk.storage.uploadfile",
                    files={"fileContent": (file_info["NAME"], file_content)},
                    auth=BASIC_AUTH,
                    timeout=30
                )
                
                if upload_response.status_code == 200:
                    file_id = upload_response.json().get("result", {}).get("ID")
                    if file_id:
                        attached_files.append(file_id)
            except Exception as e:
                logging.error(f"Ошибка обработки файла: {e}")
                continue

        # 4. Прикрепление к сделке
        if attached_files:
            update_response = requests.post(
                f"{BITRIX_API_URL}crm.deal.update",
                json={
                    "id": data["deal_id"],
                    "fields": {FILE_FIELD_ID: attached_files}
                },
                auth=BASIC_AUTH,
                timeout=10
            )
            
            if update_response.status_code == 200:
                return jsonify({
                    "status": "success",
                    "files_attached": len(attached_files)
                })

        return jsonify({"error": "Нет файлов для прикрепления"}), 400

    except Exception as e:
        logging.exception("Ошибка в обработчике")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=10000)
