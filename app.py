import os
import datetime
import traceback

from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
from telegram import Bot, InputMediaPhoto

load_dotenv()

app = Flask(__name__)

# ==== Считываем переменные окружения ====
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "")  # например: https://vas-dom.bitrix24.ru/rest/1/gq2ixv9nypiimwi9/
BITRIX_DEAL_UPDATE_URL = os.getenv("BITRIX_DEAL_UPDATE_URL", "")  # например: https://vas-dom.bitrix24.ru/rest/1/2swwzy9rhrawva6y/crm.deal.update
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")  # например: 7828348940:AAGAu_pwZniOoBSNaHCMngN-pcVDiL_fdZg
CHAT_ID = os.getenv("CHAT_ID", "")                        # например: -1002392406295
BASIC_AUTH_LOGIN = os.getenv("BASIC_AUTH_LOGIN", "")      # например: maslovmaksim92@yandex.ru
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "")# например: 123456

# Ваше пользовательское поле для файлов в Сделке
CUSTOM_FILE_FIELD = "UF_CRM_1740994275251"


def upload_file_to_bitrix(file_content, file_name="photo.jpg"):
    """
    1) Загружает файл в Битрикс24 через disk.storage.uploadfile
    2) Возвращает ID загруженного файла
    """
    try:
        # ID хранилища (пример: 123). Нужно узнать реальный storage ID,
        # куда можно загружать (например, общий диск, диск CRM и т.д.).
        storage_id = 123

        upload_url = f"{BITRIX_WEBHOOK_URL}disk.storage.uploadfile"
        # Для multipart/form-data:
        files_data = {
            "id": (None, str(storage_id)),
            "fileContent": (file_name, file_content),
        }
        resp = requests.post(upload_url, files=files_data)
        data = resp.json()

        if "result" in data and "ID" in data["result"]:
            return data["result"]["ID"]
        else:
            print(f"Ошибка загрузки файла в Битрикс24: {data}")
            return None

    except Exception as e:
        print("Ошибка в upload_file_to_bitrix:", e)
        traceback.print_exc()
        return None


def attach_files_to_deal(deal_id, file_ids):
    """
    Привязывает список file_ids к пользовательскому полю сделки.
    """
    try:
        payload = {
            "id": deal_id,
            "fields": {
                # Ваше поле для файлов
                CUSTOM_FILE_FIELD: file_ids
            }
        }
        resp = requests.post(BITRIX_DEAL_UPDATE_URL, json=payload)
        data = resp.json()

        if data.get("result", False) is True:
            print(f"Файлы {file_ids} успешно прикреплены к сделке {deal_id}.")
            return True
        else:
            print(f"Ошибка при обновлении сделки: {data}")
            return False

    except Exception as e:
        print("Ошибка в attach_files_to_deal:", e)
        traceback.print_exc()
        return False


@app.route("/upload_photos", methods=["POST"])
def upload_photos():
    """
    Основной эндпоинт:
    1) Получает folder_id + deal_id
    2) Скачивает файлы из папки
    3) Шлёт их в Телеграм
    4) Загружает в Disk Bitrix24
    5) Привязывает к сделке
    """
    data = request.get_json()
    folder_id = data.get("folder_id")
    deal_id = data.get("deal_id")

    if not folder_id or not deal_id:
        return jsonify({"status": "error", "message": "folder_id или deal_id отсутствуют"}), 400

    # ==== 1) Получаем файлы из папки Bitrix24 ====
    try:
        get_children_url = f"{BITRIX_WEBHOOK_URL}disk.folder.getchildren"
        resp = requests.post(get_children_url, json={"id": folder_id})
        result = resp.json()
        file_items = [f for f in result.get("result", []) if f.get("TYPE") == 2]
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Ошибка при получении списка файлов", "details": str(e)}), 500

    if not file_items:
        return jsonify({"status": "error", "message": "В папке нет файлов"}), 404

    # ==== 2) Скачиваем файлы ====
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    media_list = []
    file_contents = []

    for idx, file_info in enumerate(file_items, start=1):
        download_url = file_info.get("DOWNLOAD_URL")
        if not download_url:
            continue
        
        full_url = f"https://vas-dom.bitrix24.ru{download_url}"
        try:
            r = requests.get(full_url, auth=HTTPBasicAuth(BASIC_AUTH_LOGIN, BASIC_AUTH_PASSWORD))
            if r.status_code == 200:
                media_list.append(InputMediaPhoto(media=r.content))
                file_contents.append(r.content)
            else:
                print(f"Ошибка загрузки файла {full_url}: {r.status_code}")
        except Exception as ex:
            print(f"Исключение при скачивании файла {full_url}: {ex}")
            traceback.print_exc()

    if not media_list:
        return jsonify({"status": "error", "message": "Не удалось скачать файлы"}), 400

    # ==== 3) Отправляем в Телеграм (группами по 10) ====
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
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Ошибка при отправке в Телеграм", "details": str(e)}), 500

    # ==== 4) Загружаем файлы в Disk Bitrix24 и получаем их ID ====
    file_ids_for_deal = []
    for idx, content in enumerate(file_contents, start=1):
        file_id = upload_file_to_bitrix(content, file_name=f"photo_{idx}.jpg")
        if file_id:
            file_ids_for_deal.append(file_id)

    # ==== 5) Прикрепляем файлы к сделке через crm.deal.update ====
    attach_ok = False
    if file_ids_for_deal:
        attach_ok = attach_files_to_deal(deal_id, file_ids_for_deal)

    return jsonify({
        "status": "ok",
        "folder_id": folder_id,
        "deal_id": deal_id,
        "files_sent_telegram": total_sent,
        "files_attached_deal": len(file_ids_for_deal),
        "deal_attach_success": attach_ok
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
