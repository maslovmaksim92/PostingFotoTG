import httpx
import os
from loguru import logger
from babel.dates import format_date
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_media_group(photo_urls, address):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("❌ Отсутствует токен или чат ID Telegram")
        return False

    if not photo_urls:
        logger.error("❌ Нет фото для отправки")
        return False

    today = datetime.now()
    russian_date = format_date(today, format='d MMMM y', locale='ru')

    caption = (
        f"🧹 Уборка завершена\n"
        f"🏠 Адрес: {address or 'Адрес не указан'}\n"
        f"📅 Дата: {russian_date}"
    )

    media = []
    for i, url in enumerate(photo_urls):
        media.append({
            "type": "photo",
            "media": url,
            "caption": caption if i == 0 else "",  # Подпись только на первом фото
            "parse_mode": "HTML"
        })

    send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMediaGroup"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "media": media
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(send_url, json=payload)
        if response.status_code == 200:
            logger.success(f"✅ Фото отправлены в Telegram ({len(photo_urls)} шт)")
            return True
        else:
            logger.error(f"❌ Ошибка отправки в Telegram: {response.text}")
            return False
