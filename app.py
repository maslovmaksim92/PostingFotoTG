import os
import datetime
import traceback
import logging

from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
from telegram import Bot, InputMediaPhoto

# Настройка логирования: выводим все сообщения уровня DEBUG и выше
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

load_dotenv()

app = Flask(__name__)

# ==== Чтение переменных окружения ====
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "").strip()  # Например: https://vas-dom.bitrix24.ru/rest/1/gq2ixv9nypiimwi9/
BITRIX_DEAL_UPDATE_URL = os.getenv("BITRIX_DEAL_UPDATE_URL", "").strip()  # Например: https://vas-dom.bitrix24.ru/rest/1/2swwzy9rhrawva6y/crm.deal.update
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()  # Токен вашего бота
CHAT_ID = os.getenv("CHAT_ID", "").strip()                        # ID чата (например, -1002392406295)
BASIC_AUTH_LOGIN = os.getenv("BASIC_AUTH_LOGIN", "").strip()        # Логин для BasicAuth
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "").strip()  # Пароль для BasicAuth

# Код пользовательского поля для файлов в сделке
CUSTOM_FILE_FIELD = "UF_CRM_1740994275251"

def upload_file_to_bitrix(file_content, file_name="photo.jpg"):
    """
    Загружает файл в Bitrix24 через метод disk.storage.uploadfile и возвращает его ID.
    Обратите внимание: storage_id нужно заменить на актуальный для вашего аккаунта!
    """
    try:
        storage_id = 123  # !!! Замените на реальный storage_id !!!
        upload_url = f"{BITRIX_WEBHOOK_URL}disk.storage.uploadfile"
        files_data = {
            "id": (None, str(storage_id)),
            "fileContent": (file_name, file_content),
        }
        logging.debug(f"Отправляем файл '{file_name}' на {upload_url} с storage_id={storage_id}")
        resp = requests.post(upload_url, files=files_data)
        data = resp.json()
        logging.debug(f"Ответ от disk.storage.uploadfile: {data}")

        if "result" in data and "ID" in data["result"]:
            file_id = data["result"]["ID"]
            logging.info(f"Файл '{file_name}' успешно загружен, ID: {file_id}")
            return file_id
        else:
            logging.error(f"Ошибка загрузки файла '{file_name}' в Bitrix24: {data}")
            return None

    except Exception as e:
        logging.exception(f"Исключение в upload_file_to_bitrix для файла '{file_name}': {e}")
        return None

def attach_files_to_deal(deal_id, file_ids):
    """
    Перезаписывает файловое поле сделки, обновляя его новым списком file_ids.
    """
    try:
        payload = {
            "id": deal_id,
            "fields": {
                CUSTOM_FILE_FIELD: file_ids
            }
        }
        logging.debug(f"Отправляем запрос crm.deal.update с payload: {payload}")
        resp = requests.post(BITRIX_DEAL_UPDATE_URL, json=payload)
        data = resp.json()
        logging.debug(f"Ответ от crm.deal.update: {data}")

        if data.get("result", False) is True:
            logging.info(f"Файлы {file_ids} успешно прикреплены к сделке {deal_id}.")
            return True
        else:
            logging.error(f"Ошибка при обновлении сделки {deal_id}: {data}")
            return False

    except Exception as e:
        logging.exception(f"Исключение в attach_files_to_deal для сделки {deal_id}: {e}")
        return False

@app.route("/upload_photos", methods=["POST"])
def upload_photos():
    """
    Эндпоинт:
      1. Принимает JSON с folder_id и deal_id.
      2. Получает список файлов из папки Bitrix24 (disk.folder.getchildren).
      3. Скачивает файлы.
      4. Отправляет фото в Telegram (группами по 10).
      5. Загружает файлы в Bitrix24 и перезаписывает поле сделки.
    """
    data = request.get_json()
    folder_id = data.get("folder_id")
    deal_id = data.get("deal_id")

    logging.info(f"Получен запрос для folder_id: {folder_id}, deal_id: {deal_id}")

    if not folder_id or not deal_id:
        logging.error("Отсутствуют folder_id или deal_id")
        return jsonify({"status": "error", "message": "folder_id или deal_id отсутствуют"}), 400

    # Получаем список файлов из папки Bitrix24
    try:
        get_children_url = f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren"
        logging.debug(f"Запрос к {get_children_url} с id: {folder_id}")
        resp = requests.post(get_children_url, json={"id": folder_id})
        result = resp.json()
        file_items = [f for f in result.get("result", []) if f.get("TYPE") == 2]
        logging.info(f"Найдено файлов в папке: {len(file_items)}")
    except Exception as e:
        logging.exception(f"Ошибка при получении файлов из папки {folder_id}: {e}")
        return jsonify({"status": "error", "message": "Ошибка при получении списка файлов", "details": str(e)}), 500

    if not file_items:
        logging.warning("В папке нет файлов")
        return jsonify({"status": "error", "message": "В папке нет файлов"}), 404

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    media_list = []
    file_contents = []

    for idx, file_info in enumerate(file_items, start=1):
        download_url = file_info.get("DOWNLOAD_URL")
        if not download_url:
            logging.warning(f"Файл без DOWNLOAD_URL, пропускаем: {file_info}")
            continue
        
        full_url = f"https://vas-dom.bitrix24.ru{download_url}"
        logging.debug(f"Скачиваем файл {idx} с {full_url}")
        try:
            r = requests.get(full_url, auth=HTTPBasicAuth(BASIC_AUTH_LOGIN, BASIC_AUTH_PASSWORD))
            if r.status_code == 200:
                media_list.append(InputMediaPhoto(media=r.content))
                file_contents.append(r.content)
                logging.info(f"Файл {idx} успешно скачан.")
            else:
                logging.error(f"Ошибка скачивания файла {full_url}: статус {r.status_code}")
        except Exception as ex:
            logging.exception(f"Исключение при скачивании файла {full_url}: {ex}")

    if not media_list:
        logging.error("Не удалось скачать ни одного файла")
        return jsonify({"status": "error", "message": "Не удалось скачать файлы"}), 400

    # Отправка файлов в Telegram
    now_str = datetime.datetime.now().strftime('%d.%m %H:%M')
    caption = f"Папка: {folder_id} ({now_str})"
    media_list[0].caption = caption
    chunk_size = 10
    total_sent = 0

    try:
        for i in range(0, len(media_list), chunk_size):
            chunk = media_list[i:i+chunk_size]
            bot.send_media_group(chat_id=CHAT_ID, media=chunk)
            total_sent += len(chunk)
        logging.info(f"Отправлено {total_sent} файлов в Telegram.")
    except Exception as e:
        logging.exception(f"Ошибка при отправке файлов в Telegram: {e}")
        return jsonify({"status": "error", "message": "Ошибка при отправке в Telegram", "details": str(e)}), 500

    # Загружаем файлы в Bitrix24 и получаем их ID
    file_ids_for_deal = []
    for idx, content in enumerate(file_contents, start=1):
        logging.debug(f"Загружаем файл {idx} в Bitрикс24")
        file_id = upload_file_to_bitrix(content, file_name=f"photo_{idx}.jpg")
        if file_id:
            file_ids_for_deal.append(file_id)
        else:
            logging.error(f"Не удалось загрузить файл {idx} в Bitрикс24.")

    # Обновляем сделку, перезаписывая файловое поле новыми file_ids
    attach_ok = False
    if file_ids_for_deal:
        attach_ok = attach_files_to_deal(deal_id, file_ids_for_deal)
    else:
        logging.error("Нет file_ids для обновления сделки.")

    response_payload = {
        "status": "ok",
        "folder_id": folder_id,
        "deal_id": deal_id,
        "files_sent_telegram": total_sent,
        "files_attached_deal": len(file_ids_for_deal),
        "deal_attach_success": attach_ok
    }
    logging.info(f"Завершено обновление сделки, ответ: {response_payload}")
    return jsonify(response_payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
