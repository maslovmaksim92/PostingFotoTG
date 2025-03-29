import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    filename="logs/app.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

app = Flask(__name__)

# Переменные окружения
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "").strip()
BITRIX_DEAL_UPDATE_URL = os.getenv("BITRIX_DEAL_UPDATE_URL", "").strip()
BASIC_AUTH_LOGIN = os.getenv("BASIC_AUTH_LOGIN", "").strip()
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "").strip()

# Кастомное поле для файлов
CUSTOM_FILE_FIELD = "UF_CRM_1740994275251"

@app.route("/", methods=["GET"])
def index():
    return "Сервис работает ✅", 200


def download_file(url):
    logging.info("📥 Пытаюсь скачать файл: %s", url)
    try:
        r = requests.get(url, auth=HTTPBasicAuth(BASIC_AUTH_LOGIN, BASIC_AUTH_PASSWORD))
        if r.status_code == 200:
            return r.content
        else:
            logging.error("❌ Ошибка при скачивании файла (%s): код %s", url, r.status_code)
            return None
    except Exception as ex:
        logging.exception("🔥 Исключение при скачивании файла: %s", ex)
        return None


def upload_file_to_bitrix(file_content, file_name, storage_id=3):
    logging.info("⬆️ Загружаю файл в Bitrix24: %s", file_name)
    try:
        upload_url = f"{BITRIX_WEBHOOK_URL}disk.storage.uploadfile"
        files_data = {
            "id": (None, str(storage_id)),
            "fileContent": (file_name, file_content),
        }
        resp = requests.post(upload_url, files=files_data)
        data = resp.json()
        logging.debug("📦 Ответ Bitrix disk.storage.uploadfile: %s", data)

        if "result" in data and "ID" in data["result"]:
            return data["result"]["ID"]
        else:
            logging.error("❌ Не удалось загрузить файл в Bitrix: %s", data)
            return None
    except Exception as e:
        logging.exception("🔥 Исключение при загрузке файла в Bitrix: %s", e)
        return None


def attach_files_to_deal(deal_id, file_ids):
    logging.info("📎 Прикрепляю файлы к сделке %s", deal_id)
    try:
        payload = {
            "id": deal_id,
            "fields": {CUSTOM_FILE_FIELD: file_ids}
        }
        resp = requests.post(BITRIX_DEAL_UPDATE_URL, json=payload)
        data = resp.json()
        logging.debug("📬 Ответ Bitrix crm.deal.update: %s", data)
        return data.get("result", False)
    except Exception as e:
        logging.exception("🔥 Исключение при прикреплении файлов к сделке: %s", e)
        return False


@app.route("/attach_files", methods=["POST"])
def attach_files():
    data = request.get_json(silent=True)

    if data is None:
        logging.error("❌ Формат запроса не JSON: %s", request.data.decode("utf-8"))
        return jsonify({"status": "error", "message": "Формат запроса не JSON"}), 400

    folder_id = data.get("folder_id")
    deal_id = data.get("deal_id")

    logging.info(f"🔍 Получен запрос: folder_id={folder_id}, deal_id={deal_id}")

    if not folder_id or not deal_id:
        logging.error("❌ Не указаны folder_id или deal_id")
        return jsonify({"status": "error", "message": "Не указаны folder_id или deal_id"}), 400

    # Получаем список файлов из папки
    try:
        resp = requests.post(
            f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren",
            json={"id": folder_id}
        )
        result_json = resp.json()
        files_info = [f for f in result_json.get("result", []) if f.get("TYPE") == 2]
        logging.info(f"📂 В папке {folder_id} найдено файлов: {len(files_info)}")
    except Exception as e:
        logging.exception("🔥 Ошибка при получении списка файлов из папки:")
        return jsonify({"status": "error", "message": "Ошибка получения списка файлов"}), 500

    if not files_info:
        logging.error("📁 Папка пуста")
        return jsonify({"status": "error", "message": "Папка пуста"}), 404

    file_ids_for_deal = []

    for file_info in files_info:
        file_url = f"https://vas-dom.bitrix24.ru{file_info.get('DOWNLOAD_URL')}"
        file_name = os.path.basename(urlparse(file_url).path)
        file_content = download_file(file_url)

        if file_content:
            file_id = upload_file_to_bitrix(file_content, file_name)
            if file_id:
                file_ids_for_deal.append(file_id)
                logging.info(f"✅ Файл '{file_name}' успешно загружен (ID={file_id})")
            else:
                logging.error(f"❌ Ошибка загрузки файла '{file_name}' в Bitrix")
        else:
            logging.error(f"❌ Не удалось скачать файл '{file_name}'")

    if not file_ids_for_deal:
        logging.error("❌ Ни один файл не был прикреплён к сделке")
        return jsonify({"status": "error", "message": "Не удалось прикрепить файлы"}), 500

    attach_success = attach_files_to_deal(deal_id, file_ids_for_deal)
    logging.info("📌 Результат прикрепления к сделке %s: %s", deal_id, "успех" if attach_success else "ошибка")

    return jsonify({
        "status": "ok" if attach_success else "error",
        "folder_id": folder_id,
        "deal_id": deal_id,
        "files_attached": len(file_ids_for_deal),
        "attach_success": attach_success
    }), 200 if attach_success else 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
