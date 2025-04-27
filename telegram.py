import os
import loguru
import httpx
from datetime import datetime
from babel.dates import format_date

TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def build_caption(address: str) -> str:
    today = datetime.now()
    russian_date = format_date(today, format='d MMMM y', locale='ru')
    return (
        f"\U0001F9F9 Уборка завершена\n"
        f"\U0001F3E0 Адрес: {address or 'Не указан'}\n"
        f"\U0001F4C5 Дата: {russian_date}\n"
        f"\n✅ Благодарим за чистоту! Ваш Дом 🏠"
    )

async def send_media_group(photos: list, address: str) -> bool:
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        loguru.logger.error("❌ Нет настроек для Telegram")
        return False

    caption = build_caption(address)
    media = []

    for idx, photo in enumerate(photos):
        item = {
            "type": "photo",
            "media": photo,
        }
        if idx == 0:
            item["caption"] = caption
            item["parse_mode"] = "HTML"
        media.append(item)

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMediaGroup"
    payload = {
        "chat_id": TG_CHAT_ID,
        "media": media
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                loguru.logger.success(f"✅ Фото отправлены в Telegram ({len(photos)} шт)")
                return True
            else:
                loguru.logger.error(f"❌ Ошибка отправки в Telegram: {response.text}")
                return False
    except Exception as e:
        loguru.logger.exception("❌ Ошибка отправки сообщений в Telegram")
        return False
