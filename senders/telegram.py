from utils.telegram_client import send_photo, send_message
from utils.bitrix import get_deal_photos, get_deal_info
from utils.ai import generate_message
from loguru import logger


async def send_cleaning_report(deal_id: int):
    try:
        photos = await get_deal_photos(deal_id)
        deal_info = await get_deal_info(deal_id)

        # 1. Отправляем фото + основное сообщение
        for photo in photos:
            await send_photo(photo)

        address = deal_info.get("address", "[адрес неизвестен]")
        person = deal_info.get("responsible", "[ответственный не найден]")
        await send_message(f"🧹 Уборка завершена по адресу: {address}\nОтветственный: {person}")

        # 2. Промт GPT и вдохновляющее сообщение
        prompt = (
            "Напиши короткое вдохновляющее сообщение. Можешь использовать стихи, байт на отзывы, мотивацию или похвалу труда уборщиков."
        )
        gpt_message = await generate_message(prompt)
        await send_message(f"🤖 GPT говорит: {gpt_message}")

    except Exception as e:
        logger.exception(f"Ошибка при отправке отчёта по сделке {deal_id}: {e}")
