from utils.telegram_client import send_message, send_photo
from utils.bitrix import get_deal_info, get_deal_photos
from utils.ai import generate_gpt_text
from loguru import logger


async def send_cleaning_report(deal_id: int) -> None:
    logger.info(f"🚀 Старт отправки отчёта по сделке {deal_id}")
    try:
        deal = get_deal_info(deal_id)
        logger.debug(f"📄 Получены данные сделки: {deal}")

        address = deal.get("UF_CRM_1686038818")
        responsible = deal.get("ASSIGNED_BY_ID")
        logger.debug(f"📍 Адрес: {address}, 👷 Ответственный ID: {responsible}")

        photos = get_deal_photos(deal)
        logger.debug(f"📸 Найдено фото: {len(photos)} шт.")

        message = f"\n<b>🧹 Уборка подъездов завершена</b>\n"
        if address:
            message += f"<b>📍 Адрес:</b> {address}\n"
        if responsible:
            message += f"<b>👷 Ответственный:</b> {responsible}\n"
        message += f"<b>📅 Дата:</b> сегодня\n\n"

        logger.info("🤖 Генерация текста от GPT-3.5...")
        gpt_text = await generate_gpt_text()
        logger.debug(f"📨 GPT-сообщение: {gpt_text}")

        message += gpt_text

        logger.info("📤 Отправка в Telegram...")
        await send_photo(photos, caption=message)
        logger.success("✅ Отправка завершена успешно")

    except Exception as e:
        logger.exception(f"❌ Ошибка при отправке отчёта по сделке {deal_id}: {e}")