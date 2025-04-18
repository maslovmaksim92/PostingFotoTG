import os
import httpx
from loguru import logger

TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

async def send_photo(image_url: str, caption: str) -> bool:
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        logger.warning("Telegram credentials are missing")
        return False

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TG_CHAT_ID,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            if result.get("ok"):
                logger.info(f"📷 Фото отправлено в Telegram: {image_url}")
                return True
            else:
                logger.error(f"❌ Ошибка Telegram: {result}")
                return False
    except Exception as e:
        logger.exception("Ошибка при отправке фото в Telegram")
        return False