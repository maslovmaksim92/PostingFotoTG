from bitrix import get_files_from_folder, attach_media_to_deal, get_address_from_deal
from telegram import send_media_group
from loguru import logger
import asyncio

def upload_folder_to_deal(deal_id: int, folder_id: int):
    try:
        files = get_files_from_folder(folder_id)
        if not files:
            logger.warning(f"⚠️ Нет файлов в папке {folder_id} для сделки {deal_id}")
            return

        attach_media_to_deal(deal_id, files)

        # Отправка в Telegram
        address = get_address_from_deal(deal_id)
        photo_urls = [f["download_url"] for f in files if f.get("download_url")]
        if photo_urls:
            logger.info(f"📤 Пытаемся отправить фото в Telegram для сделки {deal_id}")
            asyncio.run(send_media_group(photo_urls, address))

        logger.info(f"✅ Файлы из папки {folder_id} прикреплены и отправлены для сделки {deal_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки файлов для сделки {deal_id}: {e}")
        raise
