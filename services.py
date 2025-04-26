from bitrix import get_files_from_folder, attach_media_to_deal
from loguru import logger

def upload_folder_to_deal(deal_id: int, folder_id: int):
    try:
        files = get_files_from_folder(folder_id)
        if not files:
            logger.warning(f"⚠️ Нет файлов в папке {folder_id} для сделки {deal_id}")
            return
        attach_media_to_deal(deal_id, files)
        logger.info(f"✅ Файлы из папки {folder_id} прикреплены к сделке {deal_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки файлов для сделки {deal_id}: {e}")
        raise