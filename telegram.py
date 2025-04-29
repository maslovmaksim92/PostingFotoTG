import os
import httpx
from loguru import logger
from dotenv import load_dotenv
from datetime import datetime
from babel.dates import format_date

load_dotenv()

TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")

async def send_media_group(photos, address: str):
    if not address:
        logger.warning("📭 Адрес объекта не указан, используем fallback")
        address = "Адрес не указан"

    today = datetime.now()
    russian_date = format_date(today, format='d MMMM y', locale='ru')
    caption = (
        f"🧹 Уборка завершена\n"
        f"🏠 Адрес: {address}\n"
        f"📅 Дата: {russian_date}"
    )

    media = [
        {
            "type": "photo",
            "media": url,
            "caption": caption if idx == 0 else "",
            "parse_mode": "HTML"
        }
        for idx, url in enumerate(photos)
    ]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMediaGroup",
                json={"chat_id": TG_CHAT_ID, "media": media}
            )
            if resp.status_code == 200:
                logger.success(f"✅ Фото отправлены в Telegram ({len(photos)} шт)")
            else:
                logger.error(f"❌ Ошибка отправки в Telegram: {resp.text}")
    except Exception as e:
        logger.exception(f"❌ Ошибка HTTP при отправке в Telegram: {e}")
