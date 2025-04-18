import httpx
import os
from loguru import logger

TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")


async def send_photo(image_url: str, address: str):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        logger.warning("Telegram credentials are missing")
        return False

    caption = (
        f"\U0001F9F9 <b>Уборка подъездов завершена</b>\n"
        f"\U0001F3E0 <b>Адрес:</b> {address}\n"
        f"\U0001F4C5 <b>Дата:</b> сегодня"
    )

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TG_CHAT_ID,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "HTML"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=payload)
            response.raise_for_status()
            result = response.json()
            if result.get("ok"):
                logger.info("\u2705 Telegram: сообщение отправлено")
                return True
            else:
                logger.error(f"Telegram API error: {result}")
                return False
    except Exception as e:
        logger.exception("Ошибка отправки в Telegram")
        return False