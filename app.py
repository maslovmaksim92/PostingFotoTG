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
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8"
)

app = Flask(__name__)

BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL").strip()
BITRIX_DEAL_UPDATE_URL = os.getenv("BITRIX_DEAL_UPDATE_URL").strip()
BASIC_AUTH_LOGIN = os.getenv("BASIC_AUTH_LOGIN").strip()
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD").strip()

CUSTOM_FILE_FIELD = "UF_CRM_1740994275251"

@app.route("/", methods=["GET"])
def index():
    return "Сервис активен", 200

def download_file(url):
    try:
        logging.debug(f"Скачиваю файл: {url}")
        r = requests.get(url, auth=HTTPBasicAuth(BASIC_AUTH_LOGIN, BASIC_AUTH_PASSWORD))
        if r.status_code == 200:
            return r.content
        else:
            logging.error(f"Ошибка скачивания файла ({url}): {r.status_code}")
            return None
    except Exception as ex:
        logging.exception(f"Ошибка при скачивании файла ({url}): {ex}")
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
        logging.debug(f"Ответ disk.storage.uploadfile: {data}")

        if "result" in data and "ID" in data["result"]:
            return data["result"]["ID"]
        else:
            logging.error(f"Ошибка загрузки файла в Bitrix24: {data}")
            return None
    except Exception as e:
        logging.exception(f"Исключение при upload_file_to_bitrix: {e}")
        return None

def attach_files_to_deal(deal_id, file_ids):
    try:
        payload = {
            "id": deal_id,
            "fields": {CUSTOM_FILE_FIELD: file_ids}
        }
        resp = requests.post(BITRIX_DEAL_UPDATE_URL, json=payload)
        data = resp.json()
        logging.debug(f"Ответ crm.deal.update: {data}")
        return data.get("result", False)
    except Exception as e:
        logging.exception(f"Исключение в attach_files_to_deal: {e}")
        return False

@app.route("/attach_files", methods=["POST"])
def attach_files():
    data = request.get_json(silent=True)

    if data is None:
        logging.error(f"JSON-данные не распознаны: {request.data.decode('utf-8')}")
        return jsonify({"status": "error", "message": "Ошибка: данные не в формате JSON"}), 400

    folder_id = data.get("folder_id")
    deal_id = data.get("deal_id")

    logging.info(f"Получены данные: folder_id={folder_id}, deal_id={deal_id}")

    if not folder_id or not deal_id:
        logging.error("Не указан folder_id или deal_id в запросе")
        return jsonify({"status": "error", "message": "Отсутствуют folder_id или deal_id"}), 400

    try:
        resp = requests.post(
            f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren", json={"id": folder_id}
        )
        files_info = [f for f in resp.json().get("result", []) if f.get("TYPE") == 2]
        logging.info(f"Файлов в папке {folder_id} найдено: {len(files_info)}")
    except Exception as e:
        logging.exception(f"Ошибка получения списка файлов из папки {folder_id}: {e}")
        return jsonify({"status": "error", "message": "Ошибка получения списка файлов"}), 500

    if not files_info:
        logging.error(f"Папка {folder_id} пуста.")
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
                logging.info(f"Файл '{file_name}' успешно загружен в сделку (ID {file_id})")
            else:
                logging.error(f"Не удалось загрузить файл '{file_name}' обратно в Битрикс.")
        else:
            logging.error(f"Не удалось скачать файл '{file_name}'")

    if not file_ids_for_deal:
        logging.error("Не удалось загрузить ни одного файла.")
        return jsonify({"status": "error", "message": "Не удалось загрузить файлы"}), 500

    attach_success = attach_files_to_deal(deal_id, file_ids_for_deal)
    logging.info(f"Прикрепление файлов к сделке ({deal_id}): {'успешно' if attach_success else 'ошибка'}")

    return jsonify({
        "status": "ok",
        "folder_id": folder_id,
        "deal_id": deal_id,
        "files_attached": len(file_ids_for_deal),
        "attach_success": attach_success
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
