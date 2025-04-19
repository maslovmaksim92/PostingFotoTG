from loguru import logger
import aiohttp
from typing import List, Optional

from config import settings


async def send_message(text: str) -> None:
    """
    Отправка текстового сообщения в Telegram-чат
    """
    url = f"https://api.telegram.org/bot{settings.TG_GITHUB_BOT}/sendMessage"
    payload = {
        "chat_id": settings.TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            result = await response.json()
            if not result.get("ok"):
                logger.error(f"Telegram API error: {result}")
            else:
                logger.info("📤 Текстовое сообщение отправлено в Telegram")


async def send_photo(photo_urls: List[str], caption: Optional[str] = None) -> None:
    """
    Отправка списка фото в Telegram с необязательной подписью
    """
    if not photo_urls:
        logger.warning("Пустой список фото, отправка в Telegram пропущена")
        return

    async with aiohttp.ClientSession() as session:
        for idx, photo_url in enumerate(photo_urls):
            payload = {
                "chat_id": settings.TG_CHAT_ID,
                "photo": photo_url,
            }
            if idx == 0 and caption:
                payload["caption"] = caption
                payload["parse_mode"] = "HTML"

            async with session.post(
                f"https://api.telegram.org/bot{settings.TG_GITHUB_BOT}/sendPhoto",
                data=payload,
            ) as response:
                result = await response.json()
                if not result.get("ok"):
                    logger.error(f"Telegram API photo error: {result}")
                else:
                    logger.info(f"📸 Фото {idx + 1}/{len(photo_urls)} успешно отправлено")