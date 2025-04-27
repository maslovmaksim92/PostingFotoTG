import time
import requests
import logging
from utils import bitrix_call

logger = logging.getLogger(__name__)

def get_files_from_folder(folder_id):
    try:
        response = bitrix_call('disk.folder.getchildren', {"id": folder_id})
        files = response.get('result', [])
        logger.debug(f"\U0001f4cb Найдено файлов в папке {folder_id}: {len(files)} файлов")
        return files
    except Exception as e:
        logger.error(f"\u274c Ошибка при получении файлов из папки {folder_id}: {str(e)}")
        return []

def attach_media_to_deal(deal_id, folder_id):
    logger.info(f"\U0001f4ce Прикрепление файлов напрямую по ID к сделке {deal_id}")
    files = get_files_from_folder(folder_id)
    if not files:
        logger.warning(f"\u26a0\ufe0f Нет файлов для прикрепления в папке {folder_id}")
        return

    file_ids = [file['ID'] for file in files]

    fields = {
        'fields': {
            'UF_CRM_1740994275251': file_ids
        }
    }
    try:
        response = bitrix_call('crm.deal.update', {"id": deal_id, **fields})
        logger.info(f"\u2705 Файлы прикреплены к сделке {deal_id}: {file_ids}")

        logger.info("\u23f3 Ждём 2 секунды перед проверкой состояния...")
        time.sleep(2)

        attached = check_files_attached(deal_id)
        if not attached:
            logger.warning(f"\u26a0\ufe0f После первой попытки файлы не прикреплены, пробуем повторно...")
            time.sleep(3)
            response = bitrix_call('crm.deal.update', {"id": deal_id, **fields})
            logger.info("\u23f3 Ждём ещё 2 секунды...")
            time.sleep(2)
            attached = check_files_attached(deal_id)
            if attached:
                logger.info(f"\u2705 Файлы прикреплены после повторной попытки к сделке {deal_id}")
            else:
                logger.error(f"\u274c После повтора файлы всё ещё не прикреплены к сделке {deal_id}")
    except Exception as e:
        logger.error(f"\u274c Ошибка при прикреплении файлов к сделке {deal_id}: {str(e)}")

    logger.info(f"\u2705 Файлы из папки {folder_id} прикреплены к сделке {deal_id}")

def check_files_attached(deal_id):
    try:
        deal = bitrix_call('crm.deal.get', {"id": deal_id})
        files = deal.get('result', {}).get('UF_CRM_1740994275251', [])
        logger.debug(f"\U0001f4cb Состояние файлов в сделке {deal_id}: {files}")
        return bool(files)
    except Exception as e:
        logger.error(f"\u274c Ошибка проверки состояния прикрепленных файлов в сделке {deal_id}: {str(e)}")
        return False