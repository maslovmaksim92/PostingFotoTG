import os
import datetime
import traceback
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
from telegram import Bot, InputMediaPhoto

# Настройка логирования в файл app.log
logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8"
)

load_dotenv()

app = Flask(__name__)

# ==== Чтение переменных окружения ====
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL").strip()
BITRIX_DEAL_UPDATE_URL = os.getenv("BITRIX_DEAL_UPDATE_URL").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN").strip()
CHAT_ID = os.getenv("CHAT_ID").strip()
BASIC_AUTH_LOGIN = os.getenv("BASIC_AUTH_LOGIN").strip()
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD").strip()

# Код поля в сделке для файлов
CUSTOM_FILE_FIELD = "UF_CRM_1740994275251"

# Количество потоков
MAX_WORKERS = 4

@app.route("/", methods=["GET"])
def index():
    return "Flask app is running. Use POST /upload_photos", 200

def upload_file_to_bitrix(file_content, file_name="photo.jpg"):
    try:
        storage_id = 3  # <-- Замени на реальный storage_id
        upload_url = f"{BITRIX_WEBHOOK_URL}disk.storage.uploadfile"
        files_data = {
            "id": (None, str(storage_id)),
            "fileContent": (file_name, file_content),
        }
        logging.debug(f"Загрузка файла '{file_name}' на Bitrix24...")
        resp = requests.post(upload_url, files=files_data)
        data = resp.json()
        logging.debug(f"Ответ disk.storage.uploadfile: {data}")

        return data.get("result", {}).get("ID")
    except Exception as e:
        logging.exception(f"Исключение в upload_file_to_bitrix: {e}")
        return None

def attach_files_to_deal(deal_id, file_ids):
    try:
        payload = {
            "id": deal_id,
            "fields": {CUSTOM_FILE_FIELD: file_ids}
        }
        logging.debug(f"Обновляем сделку {deal_id} файлами {file_ids}")
        resp = requests.post(BITRIX_DEAL_UPDATE_URL, json=payload)
        data = resp.json()
        logging.debug(f"Ответ crm.deal.update: {data}")

        return data.get("result", False)
    except Exception as e:
        logging.exception(f"Исключение в attach_files_to_deal: {e}")
        return False

def download_file(full_url):
    try:
        r = requests.get(full_url, auth=HTTPBasicAuth(BASIC_AUTH_LOGIN, BASIC_AUTH_PASSWORD))
        if r.status_code == 200:
            return r.content
        logging.error(f"Ошибка скачивания: {full_url}, статус {r.status_code}")
        return None
    except Exception as ex:
        logging.exception(f"Ошибка скачивания файла {full_url}: {ex}")
        return None

@app.route("/upload_photos", methods=["POST"])
def upload_photos():
    data = request.get_json()
    folder_id = data.get("folder_id")
    deal_id = data.get("deal_id")
    logging.info(f"Запрос: folder_id={folder_id}, deal_id={deal_id}")

    if not folder_id or not deal_id:
        return jsonify({"status": "error", "message": "folder_id или deal_id отсутствуют"}), 400

    try:
        resp = requests.post(f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren", json={"id": folder_id})
        full_response = resp.json()
        logging.debug(f"Ответ disk.folder.getchildren: {full_response}")
        files_info = [f for f in full_response.get("result", []) if f.get("TYPE") == 2]
        logging.info(f"Файлов найдено: {len(files_info)}")
    except Exception as e:
        logging.exception(f"Ошибка получения файлов из папки {folder_id}: {e}")
        return jsonify({"status": "error", "message": "Ошибка получения файлов"}), 500

    if not files_info:
        return jsonify({"status": "error", "message": "Нет файлов в папке"}), 404

    bot = Bot(TELEGRAM_BOT_TOKEN)
    media_list, file_contents = [], []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_file = {
            executor.submit(download_file, f"https://vas-dom.bitrix24.ru{f.get('DOWNLOAD_URL')}"): idx
            for idx, f in enumerate(files_info, start=1)
        }
        for future in as_completed(future_to_file):
            idx = future_to_file[future]
            content = future.result()
            if content:
                media_list.append(InputMediaPhoto(media=content))
                file_contents.append(content)
                logging.info(f"Файл {idx} скачан успешно.")

    if not media_list:
        return jsonify({"status": "error", "message": "Не удалось скачать файлы"}), 400

    media_list[0].caption = f"Фото из папки {folder_id} ({datetime.datetime.now():%d.%m %H:%M})"
    chunk_size, total_sent = 10, 0

    try:
        for i in range(0, len(media_list), chunk_size):
            bot.send_media_group(chat_id=CHAT_ID, media=media_list[i:i+chunk_size])
            total_sent += len(media_list[i:i+chunk_size])
        logging.info(f"Отправлено в Telegram: {total_sent} фото.")
    except Exception as e:
        logging.exception(f"Ошибка отправки в Telegram: {e}")
        return jsonify({"status": "error", "message": "Ошибка Telegram"}), 500

    file_ids_for_deal = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(upload_file_to_bitrix, content, f"photo_{idx}.jpg"): idx
            for idx, content in enumerate(file_contents, start=1)
        }
        for future in as_completed(futures):
            file_id = future.result()
            if file_id:
                file_ids_for_deal.append(file_id)

    attach_success = attach_files_to_deal(deal_id, file_ids_for_deal)
    logging.info(f"Прикрепление файлов к сделке: {'успешно' if attach_success else 'ошибка'}")

    return jsonify({
        "status": "ok",
        "folder_id": folder_id,
        "deal_id": deal_id,
        "files_sent_telegram": total_sent,
        "files_attached_deal": len(file_ids_for_deal),
        "deal_attach_success": attach_success
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
