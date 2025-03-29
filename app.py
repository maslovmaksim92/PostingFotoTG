import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse

# ✅ Создание папки логов
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ✅ Логгирование
log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler = logging.FileHandler(os.path.join(LOG_DIR, "app.log"), encoding="utf-8")
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])

# ✅ Flask-приложение
app = Flask(__name__)
load_dotenv()

# ✅ Переменные окружения
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "").strip()
BITRIX_DEAL_UPDATE_URL = os.getenv("BITRIX_DEAL_UPDATE_URL", "").strip()
BASIC_AUTH_LOGIN = os.getenv("BASIC_AUTH_LOGIN", "").strip()
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "").strip()
CUSTOM_FILE_FIELD = os.getenv("CUSTOM_FILE_FIELD", "UF_CRM_1740994275251")

@app.route("/", methods=["GET"])
def index():
    return "Сервис работает ✅", 200

def get_folder_id_from_deal(deal_id: str, field_code: str) -> str:
    try:
        url = f"{BITRIX_WEBHOOK_URL}crm.deal.get"
        resp = requests.post(url, json={"id": deal_id})
        data = resp.json()
        logging.debug(f"📥 Ответ crm.deal.get: {data}")

        if not data.get("result"):
            logging.error(f"❌ Не удалось получить сделку ID {deal_id}")
            return None

        value = data["result"].get(field_code)
        logging.info(f"📦 Значение поля {field_code} в сделке: {value}")

        # Если значение выглядит как ObjectId — возвращаем
        if value and value.isdigit():
            return value

        logging.warning(f"⚠️ Значение поля {field_code} не является ObjectId")
        return None
    except Exception as e:
        logging.exception(f"🔥 Ошибка при получении ObjectId папки из сделки: {e}")
        return None

def download_file(url: str):
    logging.info(f"📥 Скачивание файла: {url}")
    try:
        r = requests.get(url, auth=HTTPBasicAuth(BASIC_AUTH_LOGIN, BASIC_AUTH_PASSWORD))
        if r.status_code == 200:
            return r.content
        logging.error(f"❌ Ошибка при скачивании: {r.status_code}")
    except Exception as ex:
        logging.exception(f"🔥 Исключение при скачивании файла: {ex}")
    return None

def upload_file_to_bitrix(file_content: bytes, file_name: str, storage_id: int = 3):
    try:
        upload_url = f"{BITRIX_WEBHOOK_URL}disk.storage.uploadfile"
        files = {
            "id": (None, str(storage_id)),
            "fileContent": (file_name, file_content),
        }
        resp = requests.post(upload_url, files=files)
        data = resp.json()
        logging.debug(f"📤 Ответ disk.storage.uploadfile: {data}")
        return data.get("result", {}).get("ID")
    except Exception as e:
        logging.exception(f"🔥 Ошибка при загрузке файла: {e}")
    return None

def attach_files_to_deal(deal_id: str, file_ids: list):
    try:
        payload = {"id": deal_id, "fields": {CUSTOM_FILE_FIELD: file_ids}}
        resp = requests.post(BITRIX_DEAL_UPDATE_URL, json=payload)
        data = resp.json()
        logging.debug(f"📎 Ответ crm.deal.update: {data}")
        return data.get("result", False)
    except Exception as e:
        logging.exception(f"🔥 Ошибка при прикреплении к сделке: {e}")
    return False

@app.route("/attach_files", methods=["POST"])
def attach_files():
    data = request.get_json(silent=True)
    if data is None:
        logging.error("❌ Некорректный JSON: %s", request.data.decode("utf-8"))
        return jsonify({"status": "error", "message": "Неверный формат JSON"}), 400

    deal_id = data.get("deal_id")
    folder_id = data.get("folder_id")

    logging.info(f"🔍 Запрос: deal_id={deal_id}, folder_id={folder_id}")

    if not deal_id:
        return jsonify({"status": "error", "message": "Не указан deal_id"}), 400

    # 🧠 Если folder_id не число — пробуем получить через crm.deal.get
    if not folder_id or not folder_id.isdigit():
        logging.info("🔄 Пытаемся извлечь ObjectId папки из сделки")
        folder_id = get_folder_id_from_deal(deal_id, "UF_CRM_1743235503935")  # поле "Ссылка на папку / уборка подъездов"

    if not folder_id:
        return jsonify({"status": "error", "message": "folder_id не получен"}), 400

    try:
        resp = requests.post(f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren", json={"id": folder_id})
        result_json = resp.json()
        files_info = [f for f in result_json.get("result", []) if f.get("TYPE") == 2]
        logging.info(f"📂 Файлов в папке {folder_id}: {len(files_info)}")
    except Exception as e:
        logging.exception("🔥 Ошибка при получении списка файлов из папки")
        return jsonify({"status": "error", "message": "Ошибка получения списка файлов"}), 500

    if not files_info:
        return jsonify({"status": "error", "message": "Папка пуста"}), 404

    file_ids_for_deal = []

    for file_info in files_info:
        download_url = file_info.get("DOWNLOAD_URL")
        if not download_url:
            continue

        file_url = f"https://vas-dom.bitrix24.ru{download_url}"
        file_name = os.path.basename(urlparse(file_url).path)
        file_content = download_file(file_url)

        if file_content:
            file_id = upload_file_to_bitrix(file_content, file_name)
            if file_id:
                file_ids_for_deal.append(file_id)
                logging.info(f"✅ Файл {file_name} загружен. ID={file_id}")
            else:
                logging.error(f"❌ Ошибка загрузки файла {file_name}")
        else:
            logging.error(f"❌ Не удалось скачать файл {file_name}")

    if not file_ids_for_deal:
        return jsonify({"status": "error", "message": "Файлы не прикреплены"}), 500

    success = attach_files_to_deal(deal_id, file_ids_for_deal)
    logging.info(f"📌 Файлы прикреплены к сделке {deal_id}: {'Успешно' if success else 'Ошибка'}")

    return jsonify({
        "status": "ok" if success else "error",
        "folder_id": folder_id,
        "deal_id": deal_id,
        "files_attached": len(file_ids_for_deal),
        "attach_success": success
    }), 200 if success else 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
