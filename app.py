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

def download_file(url):
    try:
        logging.debug(f"Пробуем скачать файл: {url}")
        response = requests.get(url, auth=HTTPBasicAuth(BASIC_AUTH_LOGIN, BASIC_AUTH_PASSWORD))
        if response.status_code == 200:
            logging.debug("Файл скачан успешно.")
            return response.content
        else:
            logging.error(f"Ошибка скачивания файла: HTTP {response.status_code}")
            return None
    except Exception as ex:
        logging.exception(f"Исключение при скачивании файла: {ex}")
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
        logging.exception(f"Исключение в upload_file_to_bitrix: {e}")
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
    folder_id = request.args.get("folder_id")
    deal_id = request.args.get("deal_id")

    logging.info(f"Получен запрос на прикрепление: folder_id={folder_id}, deal_id={deal_id}")

    if not folder_id or not deal_id:
        message = "Отсутствует folder_id или deal_id в запросе"
        logging.error(message)
        return jsonify({"status": "error", "message": message}), 400

    try:
        resp = requests.post(
            f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren",
            json={"id": folder_id}
        )
        files_info = [f for f in resp.json().get("result", []) if f.get("TYPE") == 2]
        logging.info(f"Найдено файлов для переноса: {len(files_info)}")
    except Exception as e:
        message = f"Ошибка при получении файлов из папки: {e}"
        logging.exception(message)
        return jsonify({"status": "error", "message": message}), 500

    if not files_info:
        message = "Файлы в папке не найдены"
        logging.error(message)
        return jsonify({"status": "error", "message": message}), 404

    file_ids_for_deal = []
    for file_info in files_info:
        file_url = f"https://vas-dom.bitrix24.ru{file_info.get('DOWNLOAD_URL')}"
        file_name = os.path.basename(urlparse(file_url).path)
        logging.debug(f"Обрабатывается файл: {file_name}")

        content = download_file(file_url)
        if not content:
            logging.error(f"Не удалось скачать файл: {file_name}")
            continue

        file_id = upload_file_to_bitrix(content, file_name)
        if file_id:
            file_ids_for_deal.append(file_id)
            logging.info(f"Файл '{file_name}' успешно загружен. ID в Bitrix24: {file_id}")
        else:
            logging.error(f"Ошибка загрузки файла обратно в Bitrix24: {file_name}")

    if not file_ids_for_deal:
        message = "Ни один файл не удалось загрузить в Bitrix24"
        logging.error(message)
        return jsonify({"status": "error", "message": message}), 500

    attach_success = attach_files_to_deal(deal_id, file_ids_for_deal)
    if attach_success:
        message = "Файлы успешно прикреплены к сделке"
        logging.info(message)
        return jsonify({"status": "ok", "message": message, "attached_files": len(file_ids_for_deal)})
    else:
        message = "Ошибка при прикреплении файлов к сделке"
        logging.error(message)
        return jsonify({"status": "error", "message": message}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
