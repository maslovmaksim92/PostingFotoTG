import os
from flask import Flask, request, jsonify
import requests
from requests.auth import HTTPBasicAuth

app = Flask(__name__)

# Конфигурация
BITRIX_API_URL = os.getenv("BITRIX_WEBHOOK_URL")
BASIC_AUTH = HTTPBasicAuth(os.getenv("LOGIN"), os.getenv("PASSWORD"))
FILE_FIELD = "UF_CRM_1740994275251"  # Поле для прикрепления файлов

@app.route("/webhook/disk", methods=["POST"])
def handle_webhook():
    data = request.json
    if not data or "folder_id" not in data or "deal_id" not in data:
        return jsonify({"error": "Invalid data"}), 400

    # 1. Получаем файлы из папки
    files = requests.post(
        f"{BITRIX_API_URL}disk.folder.getchildren",
        json={"id": data["folder_id"]},
        auth=BASIC_AUTH
    ).json().get("result", [])

    # 2. Фильтруем только файлы (не папки)
    file_ids = []
    for f in files:
        if f.get("TYPE") == 2:  # TYPE=2 означает файл
            # 3. Загружаем каждый файл
            content = requests.get(
                f"https://{urlparse(BITRIX_API_URL).netloc}{f['DOWNLOAD_URL']}",
                auth=BASIC_AUTH
            ).content
            
            upload = requests.post(
                f"{BITRIX_API_URL}disk.storage.uploadfile",
                files={"fileContent": (f["NAME"], content)},
                auth=BASIC_AUTH
            ).json()
            
            if upload.get("result"):
                file_ids.append(upload["result"]["ID"])

    # 4. Прикрепляем к сделке
    if file_ids:
        requests.post(
            f"{BITRIX_API_URL}crm.deal.update",
            json={
                "id": data["deal_id"],
                "fields": {FILE_FIELD: file_ids}
            },
            auth=BASIC_AUTH
        )
    
    return jsonify({"status": "success", "files_added": len(file_ids)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
