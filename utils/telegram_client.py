import os
import httpx
from loguru import logger

TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

TELEGRAM_API = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"


async def send_photo_to_telegram(image_url: str, address: str):
    text = (
        f"\U0001F9F9 Уборка подъездов завершена\n"
        f"\U0001F3E0 Адрес: {address}\n"
        f"\U0001F4C5 Дата: сегодня"
    )
    logger.info(f"\U0001F4F7 Отправка в Telegram: {image_url}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            TELEGRAM_API,
            data={"chat_id": TG_CHAT_ID, "caption": text, "photo": image_url},
        )

    if not response.status_code == 200:
        logger.warning(f"❌ Telegram error: {response.text}")
    else:
        logger.info("✅ Сообщение отправлено в Telegram")