from bitrix import get_files_from_folder, attach_media_to_deal, get_address_from_deal, get_deal_fields
from telegram import send_media_group
from gpt import generate_caption
from loguru import logger

async def send_report(deal_id: int, folder_id: int):
    logger.info(f"📦 Начало формирования отчёта для сделки {deal_id}")

    files = get_files_from_folder(folder_id)
    logger.info(f"📁 Получено файлов: {len(files)}. Начинаем сборку media_group и подготовку ID")

    file_ids = attach_media_to_deal(deal_id, files)

    address = get_address_from_deal(deal_id)
    await send_media_group(deal_id, files, address)

    logger.info(f"✅ Отчёт по сделке {deal_id} завершён: {len(files)} фото отправлены, прикреплены к Bitrix")