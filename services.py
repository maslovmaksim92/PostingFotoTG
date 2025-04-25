from bitrix import get_files_from_folder, attach_media_to_deal, get_address_from_deal
from telegram import send_media_group
from loguru import logger

async def send_report(deal_id: int, folder_id: int):
    logger.info(f"📦 Начало формирования отчёта для сделки {deal_id}")

    try:
        files = get_files_from_folder(folder_id)
        logger.info(f"📁 Получено файлов: {len(files)}. Начинаем сборку media_group и подготовку ID")

        attach_media_to_deal(deal_id, files)

        address = get_address_from_deal(deal_id)
        await send_media_group(deal_id, files)

        logger.info(f"✅ Отчёт по сделке {deal_id} завершён: {len(files)} фото отправлены, прикреплены к Bitrix")

    except Exception as e:
        logger.error(f"❌ Ошибка в send_report для сделки {deal_id}: {e}")