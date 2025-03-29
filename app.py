import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse

load_dotenv()

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)

app = Flask(__name__)

# === Конфигурация ===
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "").strip()
BITRIX_DEAL_UPDATE_URL = os.getenv("BITRIX_DEAL_UPDATE_URL", "").strip()
BASIC_AUTH_LOGIN = os.getenv("BASIC_AUTH_LOGIN", "").strip()
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "").strip()

CUSTOM_FILE_FIELD = "UF_CRM_1740994275251"  # Множественное поле для файлов

@app.route("/", methods=["GET"])
def index():
    return "Сервис работает ✅", 200

def download_file(url):
    try:
        logging.info(f"📥 Загружаю файл: {url}")
        r = requests.get(url, auth=HTTPBasicAuth(BASIC_AUTH_LOGIN, BASIC_AUTH_PASSWORD))
        if r.status_code == 200:
            return r.content
        else:
            logging.error(f"❌ Ошибка загрузки файла ({url}): статус {r.status_code}")
            return None
    except Exception as ex:
        logging.exception(f"❌ Исключение при загрузке файла: {ex}")
        return None

def upload_file_to_bitrix(file_content, file_name, storage_id=3):
    try:
        upload_url = f"{BITRIX_WEBHOOK_URL}disk.storage.uploadfile"
        files_data = {
            "id": (None, str(storage_id)),
            "fileContent": (file_name, file_content),
        }
        resp = requests.post(upload_url, files=files_data)
        data = resp.json()
        logging.info(f"📤 Ответ от disk.storage.uploadfile: {data}")

        if "result" in data and "ID" in data["result"]:
            return data["result"]["ID"]
        else:
            logging.error(f"❌ Ошибка загрузки в Битрикс24: {data}")
            return None
    except Exception as e:
        logging.exception(f"❌ Ошибка при загрузке в Bitrix: {e}")
        return None

def attach_files_to_deal(deal_id, file_ids):
    try:
        payload = {
            "id": deal_id,
            "fields": {CUSTOM_FILE_FIELD: file_ids}
        }
        resp = requests.post(BITRIX_DEAL_UPDATE_URL, json=payload)
        data = resp.json()
        logging.info(f"🔗 Ответ от crm.deal.update: {data}")
        return data.get("result", False)
    except Exception as e:
        logging.exception("❌ Исключение при обновлении сделки")
        return False

@app.route("/attach_files", methods=["POST"])
def attach_files():
    if request.content_type != "application/json":
        logging.error("❌ Content-Type не application/json")
        return jsonify({"status": "error", "message": "Content-Type должен быть application/json"}), 400

    try:
        data = request.get_json(force=True)
    except Exception as e:
        logging.error(f"❌ Ошибка чтения JSON: {str(e)}")
        return jsonify({"status": "error", "message": "Невалидный JSON"}), 400

    folder_id = str(data.get("folder_id", "")).strip()
    deal_id = str(data.get("deal_id", "")).strip()

    logging.info(f"📨 Получены параметры: folder_id={folder_id}, deal_id={deal_id}")

    if not folder_id or not deal_id:
        logging.error("❌ Не указаны folder_id или deal_id")
        return jsonify({"status": "error", "message": "folder_id и deal_id обязательны"}), 400

    try:
        resp = requests.post(f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren", json={"id": folder_id})
        resp.raise_for_status()
        files_info = [f for f in resp.json().get("result", []) if f.get("TYPE") == 2]
        logging.info(f"📂 Файлов в папке {folder_id}: {len(files_info)}")
    except Exception as e:
        logging.exception("❌ Ошибка при получении списка файлов")
        return jsonify({"status": "error", "message": "Ошибка получения файлов из папки"}), 500

    if not files_info:
        logging.warning(f"⚠️ Папка {folder_id} пуста")
        return jsonify({"status": "error", "message": "Папка пуста"}), 404

    file_ids_for_deal = []

    for file_info in files_info:
        file_url = f"https://vas-dom.bitrix24.ru{file_info.get('DOWNLOAD_URL')}"
        file_name = os.path.basename(urlparse(file_url).path)
        content = download_file(file_url)

        if content:
            file_id = upload_file_to_bitrix(content, file_name)
            if file_id:
                file_ids_for_deal.append(file_id)
                logging.info(f"✅ Файл '{file_name}' успешно прикреплён к сделке (ID {file_id})")
            else:
                logging.error(f"❌ Не удалось прикрепить файл: {file_name}")
        else:
            logging.error(f"❌ Не удалось скачать файл: {file_name}")

    if not file_ids_for_deal:
        return jsonify({"status": "error", "message": "Файлы не загружены"}), 500

    result = attach_files_to_deal(deal_id, file_ids_for_deal)
    if not result:
        logging.error("❌ Ошибка при прикреплении файлов к сделке")
        return jsonify({"status": "error", "message": "Файлы не прикреплены к сделке"}), 500

    return jsonify({
        "status": "ok",
        "folder_id": folder_id,
        "deal_id": deal_id,
        "files_attached": len(file_ids_for_deal),
        "attach_success": True
    }), 200

# ❗ Не запускаем через app.run — используем gunicorn
if __name__ == "__main__":
    print("⚠️ Используй Gunicorn для запуска: gunicorn -w 1 app:app")
