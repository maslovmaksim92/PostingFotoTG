import asyncio
from datetime import datetime
from babel.dates import format_date
from loguru import logger

async def send_media_group(photos, address: str = "") -> bool:
    if not address:
        logger.warning("📭 Адрес объекта не указан, используем fallback")
        address = "Адрес не указан"

    logger.info(f"🏠 Адрес объекта для подписи: {address}")

    today = datetime.now()
    russian_date = format_date(today, format='d MMMM y', locale='ru')
    caption = (
        f"\U0001F9F9 Уборка завершена\n"
        f"\U0001F3E0 Адрес: {address}\n"
        f"\U0001F4C5 Дата: {russian_date}"
    )

    try:
        logger.info(f"📤 Отправка {len(photos)} фото в Telegram с подписью: {caption}")
        await asyncio.sleep(1)  # Заглушка вместо реальной отправки в Telegram
        logger.success(f"✅ Фото отправлены в Telegram ({len(photos)} шт)")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка отправки в Telegram: {e}")
        return False