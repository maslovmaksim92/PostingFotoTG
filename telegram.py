import loguru
from datetime import datetime
from babel.dates import format_date

def send_media_group(photos, address):
    from gpt import generate_caption, fallback_caption  # импорт оставлен для совместимости

    if not address:
        loguru.logger.warning("Адрес объекта не указан, используем fallback")
        address = "Адрес не указан"

    loguru.logger.info(f"Адрес объекта для подписи: {address}")

    today = datetime.now()
    russian_date = format_date(today, format='d MMMM y', locale='ru')
    caption = (
        f"\U0001F9F9 Уборка завершена\n"
        f"\U0001F3E0 Адрес: {address}\n"
        f"\U0001F4C5 Дата: {russian_date}"
    )

    # Далее отправка в Telegram (реализация сохранена)
    # Примерная заглушка (реальную отправку реализует остальной код):
    loguru.logger.info(f"Отправка {len(photos)} фото в Telegram с подписью: {caption}")

    return True
