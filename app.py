import os
import datetime
import traceback
from flask import Flask, request, jsonify
import requests
from telegram import Bot, InputMediaPhoto
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

app = Flask(__name__)

# Настройки из .env
BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
LOGIN = os.getenv("BASIC_AUTH_LOGIN")
PASSWORD = os.getenv("BASIC_AUTH_PASSWORD")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


@app.route('/upload_photos', methods=['POST'])
def upload_photos():
    data = request.get_json()
    folder_id = data.get("folder_id")

    if not folder_id:
        return jsonify({"status": "error", "message": "folder_id is missing"}), 400

    # Получаем список файлов в папке
    try:
        folder_url = f"{BITRIX_WEBHOOK}disk.folder.getchildren"
        response = requests.post(folder_url, json={"id": folder_id})
        result = response.json()
        files = [f for f in result.get("result", []) if f["TYPE"] == 2]
    except Exception as e:
        return jsonify({"status": "error", "message": "Failed to get files", "details": str(e)}), 500

    if not files:
        return jsonify({"status": "error", "message": "No files found"}), 404

    media = []
    for f in files:
        download_path = f.get("DOWNLOAD_URL") or f.get("DOWNLOAD_URL", f.get("DOWNLOAD_URL"))
        if not download_path:
            continue

        file_url = "https://vas-dom.bitrix24.ru" + download_path
        try:
            file_resp = requests.get(file_url, auth=HTTPBasicAuth(LOGIN, PASSWORD))
            if file_resp.status_code == 200:
                media.append(InputMediaPhoto(media=file_resp.content))
            else:
                print(f"Не удалось скачать файл: {file_url}")
        except Exception as e:
            traceback.print_exc()

    if not media:
        return jsonify({"status": "error", "message": "No valid images to send"}), 400

    # Добавляем заголовок к первому фото
    now_str = datetime.datetime.now().strftime('%d.%m %H:%M')
    caption = f"Папка: {folder_id} ({now_str})"
    media[0] = InputMediaPhoto(media=media[0].media, caption=caption)

    try:
        bot = Bot(TELEGRAM_TOKEN)
        # Разбиваем по 10
        chunk_size = 10
        for i in range(0, len(media), chunk_size):
            bot.send_media_group(chat_id=CHAT_ID, media=media[i:i+chunk_size])
        return jsonify({"status": "ok", "files_sent": len(media)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Telegram error", "details": str(e)}), 500


if __name__ == '__main__':
    app.run()
