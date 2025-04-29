import os
import httpx
from loguru import logger
from datetime import datetime
from babel.dates import format_date
from dotenv import load_dotenv

from gpt import generate_caption
from bitrix import get_address_from_deal

load_dotenv()

TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_THREAD_ID = 2636  # <--- добавлен ID топика


async def send_media_group(photos: list[str], deal_id: int):
    if not photos:
        logger.warning("⚠️ Нет фото для отправки")
        return

    try:
        address = await get_address_from_deal(deal_id)
        russian_date = format_date(datetime.now(), format='d MMMM y', locale='ru')

        try:
            gpt_text = await generate_caption(deal_id)
            if not gpt_text:
                raise ValueError("GPT вернул пустую строку")
        except Exception as e:
            logger.warning(f"⚠️ GPT не сработал, используем fallback: {e}")
            gpt_text = "Спасибо за чистоту и заботу о доме!"

        caption = (
            f"\U0001F9F9 Уборка завершена\n"
            f"\U0001F3E0 Адрес: {address or 'не указан'}\n"
            f"\U0001F4C5 Дата: {russian_date}\n\n"
            f"{gpt_text}"
        )

        media = [
            {
                "type": "photo",
                "media": url,
                **({"caption": caption, "parse_mode": "HTML"} if idx == 0 else {})
            }
            for idx, url in enumerate(photos)
        ]

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMediaGroup",
                json={
                    "chat_id": TG_CHAT_ID,
                    "message_thread_id": TG_THREAD_ID,
                    "media": media
                }
            )

        if resp.status_code == 200:
            logger.success(f"✅ Фото отправлены в Telegram ({len(photos)} шт) → в топик {TG_THREAD_ID}")
        else:
            logger.error(f"❌ Ошибка Telegram: {resp.status_code}, {await resp.text()}")

    except Exception as e:
        logger.exception(f"❌ Ошибка при отправке в Telegram: {e}")