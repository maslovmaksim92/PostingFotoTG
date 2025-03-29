import os
import logging
from flask import Flask, request, jsonify, redirect
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

BITRIX_CLIENT_ID = os.getenv("BITRIX_CLIENT_ID")
BITRIX_CLIENT_SECRET = os.getenv("BITRIX_CLIENT_SECRET")
BITRIX_REDIRECT_URI = os.getenv("BITRIX_REDIRECT_URI")

@app.route("/", methods=["GET"])
def index():
    return "Сервис работает ✅", 200


# ✅ OAuth Авторизация Bitrix
@app.route("/auth/bitrix")
def auth_bitrix():
    auth_url = f"https://oauth.bitrix.info/oauth/authorize/?client_id={BITRIX_CLIENT_ID}&response_type=code&redirect_uri={BITRIX_REDIRECT_URI}"
    return redirect(auth_url)


@app.route("/oauth/callback")
def oauth_callback():
    auth_code = request.args.get("code")
    if not auth_code:
        logging.error("❌ Код авторизации отсутствует")
        return jsonify({"status": "error", "message": "Authorization code missing"}), 400

    try:
        token_url = "https://oauth.bitrix.info/oauth/token/"
        payload = {
            "grant_type": "authorization_code",
            "client_id": BITRIX_CLIENT_ID,
            "client_secret": BITRIX_CLIENT_SECRET,
            "code": auth_code,
            "redirect_uri": BITRIX_REDIRECT_URI
        }
        response = requests.post(token_url, data=payload)
        if response.status_code != 200:
            logging.error(f"❌ Ошибка при получении токена: {response.text}")
            return jsonify({"status": "error", "message": "Token exchange failed"}), 400

        token_data = response.json()
        logging.info("✅ OAuth успешно завершён")
        return jsonify({
            "status": "success",
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "member_id": token_data.get("member_id")
        })
    except Exception as e:
        logging.exception("🔥 Ошибка в OAuth callback")
        return jsonify({"status": "error", "message": str(e)}), 500


# ✅ Работа с файлами
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

        if value and str(value).isdigit():
            return value
        logging.warning(f"⚠️ Значение поля {field_code} не ObjectId")
    except Exception as e:
        logging.exception("🔥 Ошибка получения folder_id из сделки")
    return None


def download_file(url: str):
    logging.info(f"📥 Скачивание файла: {url}")
    try:
        r = requests.get(url, auth=HTTPBasicAuth(BASIC_AUTH_LOGIN, BASIC_AUTH_PASSWORD), timeout=10)
        if r.status_code == 200:
            return r.content
        logging.error(f"❌ Ошибка загрузки файла: код {r.status_code}")
    except Exception as ex:
        logging.exception("🔥 Ошибка при скачивании файла")
    return None


def upload_file_to_bitrix(file_content: bytes, file_name: str, storage_id: int = 3):
    try:
        upload_url = f"{BITRIX_WEBHOOK_URL}disk.storage.uploadfile"
        files = {
            "id": (None, str(storage_id)),
            "fileContent": (file_name, file_content),
        }
        resp = requests.post(upload_url, files=files, timeout=10)
        data = resp.json()
        logging.debug(f"📤 Ответ disk.storage.uploadfile: {data}")
        return data.get("result", {}).get("ID")
    except Exception as e:
        logging.exception("🔥 Ошибка загрузки файла в Bitrix")
    return None


def attach_files_to_deal(deal_id: str, file_ids: list):
    try:
        payload = {"id": deal_id, "fields": {CUSTOM_FILE_FIELD: file_ids}}
        resp = requests.post(BITRIX_DEAL_UPDATE_URL, json=payload, timeout=10)
        data = resp.json()
        logging.debug(f"📎 Ответ crm.deal.update: {data}")
        return data.get("result", False)
    except Exception as e:
        logging.exception("🔥 Ошибка при прикреплении файлов")
    return False


@app.route("/attach_files", methods=["POST"])
def attach_files():
    data = request.get_json(silent=True)
    if data is None:
        logging.error("❌ Не JSON: %s", request.data.decode("utf-8"))
        return jsonify({"status": "error", "message": "Неверный формат JSON"}), 400

    deal_id = data.get("deal_id")
    folder_id = data.get("folder_id")

    logging.info(f"🔍 Получен запрос: deal_id={deal_id}, folder_id={folder_id}")

    if not deal_id:
        return jsonify({"status": "error", "message": "deal_id обязателен"}), 400

    if not folder_id or not str(folder_id).isdigit():
        logging.info("📌 Пытаемся получить folder_id через сделку")
        folder_id = get_folder_id_from_deal(deal_id, "UF_CRM_1743235503935")

    if not folder_id:
        return jsonify({"status": "error", "message": "folder_id не найден"}), 400

    try:
        resp = requests.post(f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren", json={"id": folder_id}, timeout=10)
        result_json = resp.json()
        files_info = [f for f in result_json.get("result", []) if f.get("TYPE") == 2]
        logging.info(f"📂 Найдено файлов в папке {folder_id}: {len(files_info)}")
    except Exception as e:
        logging.exception("🔥 Ошибка получения файлов из папки")
        return jsonify({"status": "error", "message": "Ошибка получения списка файлов"}), 500

    if not files_info:
        return jsonify({"status": "error", "message": "Папка пуста"}), 404

    file_ids_for_deal = []
    for file_info in files_info:
        download_url = file_info.get("DOWNLOAD_URL")
        if not download_url:
            continue

        domain = urlparse(BITRIX_WEBHOOK_URL).netloc
        file_url = f"https://{domain}{download_url}"
        file_name = os.path.basename(urlparse(file_url).path)
        file_content = download_file(file_url)

        if file_content:
            file_id = upload_file_to_bitrix(file_content, file_name)
            if file_id:
                file_ids_for_deal.append(file_id)
                logging.info(f"✅ Загружен файл {file_name}, ID={file_id}")
            else:
                logging.error(f"❌ Ошибка загрузки {file_name}")
        else:
            logging.error(f"❌ Ошибка скачивания {file_name}")

    if not file_ids_for_deal:
        return jsonify({"status": "error", "message": "Файлы не прикреплены"}), 500

    success = attach_files_to_deal(deal_id, file_ids_for_deal)
    logging.info(f"📌 Файлы прикреплены к сделке {deal_id}: {'успешно' if success else 'ошибка'}")

    return jsonify({
        "status": "ok" if success else "error",
        "deal_id": deal_id,
        "folder_id": folder_id,
        "files_attached": len(file_ids_for_deal),
        "attach_success": success
    }), 200 if success else 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
