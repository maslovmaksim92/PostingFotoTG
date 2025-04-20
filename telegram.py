import requests
import os
import json
from loguru import logger

TG_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")


def send_photos_group(photos: list, caption: str = ""):
    media = []
    files = {}
    for i, photo in enumerate(photos):
        media.append({
            "type": "photo",
            "media": f"attach://photo{i}",
            "caption": caption if i == 0 else ""
        })
        files[f"photo{i}"] = photo

    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMediaGroup"
    data = {
        "chat_id": TG_CHAT_ID,
        "media": json.dumps(media)
    }
    response = requests.post(url, data=data, files=files)
    response.raise_for_status()
    logger.info("Фотоотчёт отправлен")


def send_video(video: bytes, caption: str):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo"
    data = {
        "chat_id": TG_CHAT_ID,
        "caption": caption,
        "supports_streaming": True
    }
    files = {"video": ("report.mp4", video)}
    response = requests.post(url, data=data, files=files)
    response.raise_for_status()
    logger.info("Видео отправлено")

def send_log_to_telegram(text: str):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    logger.debug("Лог отправлен в Telegram")
