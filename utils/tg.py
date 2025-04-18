import os
import httpx
from loguru import logger

TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

TELEGRAM_API = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMediaGroup"


async def send_photo_group(image_urls: list[str], address: str):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        logger.warning("Telegram credentials are missing")
        return False

    if "|" in address:
        address = address.split("|")[0].strip()

    caption = (
        f"\U0001F9F9 <b>Уборка подъездов завершена</b>\n"
        f"\U0001F3E0 <b>Адрес:</b> {address}\n"
        f"\U0001F4C5 <b>Дата:</b> сегодня"
    )

    chunks = [image_urls[i:i + 10] for i in range(0, len(image_urls), 10)]

    async with httpx.AsyncClient() as client:
        for i, group in enumerate(chunks):
            media = []
            for idx, url in enumerate(group):
                media.append({
                    "type": "photo",
                    "media": url,
                    "caption": str(caption) if idx == 0 else None,
                    "parse_mode": "HTML"
                })

            response = await client.post(
                TELEGRAM_API,
                json={"chat_id": TG_CHAT_ID, "media": media}
            )

            if response.status_code == 200:
                logger.info(f"✅ Telegram: отправлена группа фото ({len(group)})")
            else:
                logger.error(f"❌ Telegram error: {response.text}")