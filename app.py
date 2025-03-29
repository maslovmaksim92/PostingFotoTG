import os
import logging
from flask import Flask, request, jsonify
from requests.auth import HTTPBasicAuth
import requests
from urllib.parse import urlparse

app = Flask(__name__)

# Конфигурация
BITRIX_API_URL = os.getenv("BITRIX_WEBHOOK_URL")  # URL вебхука Bitrix24
BASIC_AUTH = HTTPBasicAuth(
    os.getenv("BASIC_AUTH_LOGIN"),  # Логин для доступа к файлам
    os.getenv("BASIC_AUTH_PASSWORD")  # Пароль
)
FILE_FIELD_ID = "UF_CRM_1740994275251"  # ID поля для файлов (из вашего скриншота)

@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    try:
        data = request.json
        
        # 1. Проверка входящих данных
        if not data or "folder_id" not in data or "deal_id" not in data:
            return jsonify({"error": "Неверный формат данных"}), 400

        deal_id = data["deal_id"]
        folder_id = data["folder_id"]

        # 2. Получаем список файлов из папки
        files_response = requests.post(
            f"{BITRIX_API_URL}disk.folder.getchildren",
            json={"id": folder_id},
            auth=BASIC_AUTH
        )
        
        if files_response.status_code != 200:
            return jsonify({"error": "Ошибка получения файлов"}), 500

        files = [f for f in files_response.json().get("result", []) 
                if f.get("TYPE") == 2]  # TYPE=2 - файлы

        # 3. Обрабатываем каждый файл
        attached_files = []
        domain = urlparse(BITRIX_API_URL).netloc
        
        for file_info in files:
            # Скачиваем файл
            file_url = f"https://{domain}{file_info['DOWNLOAD_URL']}"
            file_content = requests.get(file_url, auth=BASIC_AUTH).content
            
            # Загружаем в Bitrix24
            upload_response = requests.post(
                f"{BITRIX_API_URL}disk.storage.uploadfile",
                files={
                    "fileContent": (file_info["NAME"], file_content)
                },
                auth=BASIC_AUTH
            )
            
            if upload_response.status_code == 200:
                file_id = upload_response.json().get("result", {}).get("ID")
                if file_id:
                    attached_files.append(file_id)

        # 4. Прикрепляем файлы к сделке
        if attached_files:
            update_response = requests.post(
                f"{BITRIX_API_URL}crm.deal.update",
                json={
                    "id": deal_id,
                    "fields": {
                        FILE_FIELD_ID: attached_files  # Используем правильное поле
                    }
                },
                auth=BASIC_AUTH
            )
            
            if update_response.status_code == 200:
                return jsonify({
                    "status": "success",
                    "files_attached": len(attached_files)
                })

        return jsonify({"error": "Не удалось прикрепить файлы"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
