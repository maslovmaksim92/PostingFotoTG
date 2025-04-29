import os
import httpx
from loguru import logger
from datetime import datetime
from babel.dates import format_date
from dotenv import load_dotenv

from gpt import generate_caption  # 🧠 Подключаем GPT генератор

load_dotenv()

TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")


async def send_media_group(photos: list[str], deal_id: int):
    if not photos:
        logger.warning("⚠️ Нет фото для отправки")
        return

    try:
        address = "Не указан"
        russian_date = format_date(datetime.now(), format='d MMMM y', locale='ru')

        # 🧠 Получаем подпись от GPT
        try:
            gpt_text = await generate_caption(deal_id)
            if not gpt_text:
                raise ValueError("GPT вернул пустую строку")
        except Exception as e:
            logger.warning(f"⚠️ GPT не сработал, используем fallback: {e}")
            gpt_text = f"Уборка завершена.\n📍 Адрес: неизвестен\n📅 Дата: {russian_date}"

        # ⬇️ caption добавляется только к первому фото
        media = [
            {
                "type": "photo",
                "media": url,
                **({"caption": gpt_text, "parse_mode": "HTML"} if idx == 0 else {})
            }
            for idx, url in enumerate(photos)
        ]

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMediaGroup",
                json={"chat_id": TG_CHAT_ID, "media": media}
            )

        if resp.status_code == 200:
            logger.success(f"✅ Фото отправлены в Telegram ({len(photos)} шт)")
        else:
            logger.error(f"❌ Ошибка Telegram: {resp.status_code}, {await resp.text()}")

    except Exception as e:
        logger.exception(f"❌ Ошибка при отправке медиа в Telegram: {e}")