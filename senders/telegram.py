from utils.telegram_client import send_message, send_photo
from utils.bitrix import get_deal_info, get_deal_photos
from utils.ai import generate_gpt_text
from loguru import logger


async def send_cleaning_report(deal_id: int) -> None:
    try:
        deal = get_deal_info(deal_id)
        address = deal.get("UF_CRM_1686038818")
        responsible = deal.get("ASSIGNED_BY_ID")

        photos = get_deal_photos(deal)

        message = f"\n<b>🧹 Уборка подъездов завершена</b>\n"
        if address:
            message += f"<b>📍 Адрес:</b> {address}\n"
        if responsible:
            message += f"<b>👷 Ответственный:</b> {responsible}\n"
        message += f"<b>📅 Дата:</b> сегодня\n\n"

        gpt_text = await generate_gpt_text()
        message += gpt_text

        await send_photo(photos, caption=message)

    except Exception as e:
        logger.error(f"Ошибка при отправке отчёта по сделке {deal_id}: {e}")