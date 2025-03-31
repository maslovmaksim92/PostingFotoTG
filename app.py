import os
import logging
from flask import Flask, request, jsonify
from bitrix_utils import BitrixAPI  # предположим, это твой модуль Bitrix
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

client_id = os.getenv("BITRIX_CLIENT_ID")
client_secret = os.getenv("BITRIX_CLIENT_SECRET")
redirect_uri = os.getenv("BITRIX_REDIRECT_URI")

def get_valid_token():
    access_token = os.getenv("BITRIX_ACCESS_TOKEN")
    if not access_token:
        raise ValueError("Отсутствуют токены в базе данных")
    return access_token

def get_deal_id_from_file(folder_id: str, token: str) -> str:
    logging.info("📄 Ищем ID сделки внутри папки через disk.folder.getchildren...")
    url = f"https://vas-dom.bitrix24.ru/rest/disk.folder.getchildren.json"
    params = {
        "id": folder_id,
        "auth": token
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception("Не удалось получить список файлов в папке")

    items = response.json().get("result", [])
    for item in items:
        if item['NAME'].startswith("deal") and item['NAME'].endswith(".txt"):
            file_id = item['ID']
            logging.info(f"📄 Найден файл с ID сделки: {item['NAME']} (ID файла: {file_id})")
            return read_deal_id_from_file(file_id, token)
    raise Exception("❌ Не найден файл с ID сделки в папке")

def read_deal_id_from_file(file_id: str, token: str) -> str:
    url = f"https://vas-dom.bitrix24.ru/rest/disk.file.download.json"
    params = {
        "id": file_id,
        "auth": token
    }
    response = requests.get(url, params=params, allow_redirects=False)
    download_url = response.json().get("result", {}).get("DOWNLOAD_URL")
    if not download_url:
        raise Exception("❌ Не удалось получить ссылку на скачивание файла")

    text = requests.get(download_url).text.strip()
    logging.info(f"📥 Содержимое файла: {text}")
    if text.isdigit():
        return text
    raise Exception("❌ Невалидный формат ID сделки в файле")

@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    try:
        data = request.json
        logging.info("📥 Raw data: %s", data)

        folder_id = data.get("folder_id")
        deal_id = data.get("deal_id")

        logging.info(f"🔁 Преобразованные данные: {{'folder_id': '{folder_id}', 'deal_id': '{deal_id}'}}")

        token = get_valid_token()

        if not deal_id:
            logging.info("🔍 deal_id не передан. Пытаемся получить из файла в папке...")
            deal_id = get_deal_id_from_file(folder_id, token)

        if not deal_id or not deal_id.isdigit():
            return jsonify({"error": "❌ Invalid deal_id"}), 400

        logging.info(f"✅ Итоговый deal_id: {deal_id}")
        return jsonify({"status": "ok", "deal_id": deal_id})

    except Exception as e:
        logging.error("🔥 Ошибка в handle_disk_webhook: %s", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
