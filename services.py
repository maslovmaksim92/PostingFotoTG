from bitrix import get_files_from_folder, attach_media_to_deal, update_file_links_in_deal
from telegram import send_media_group
from loguru import logger
import asyncio

async def upload_folder_to_deal(deal_id: int, folder_id: int):
    try:
        files = await get_files_from_folder(folder_id)
        if not files:
            logger.warning(f"⚠️ Нет файлов в папке {folder_id} для сделки {deal_id}")
            return

        attached_ids = await attach_media_to_deal(deal_id, files)
        logger.info(f"💎 Файлы прикреплены по ID: {attached_ids}")

        # ⏳ Ожидание проверки (оставим для логов)
        logger.info("⏳ Ждём 2 секунды для проверки состояния файлов...")
        await asyncio.sleep(2)

        photo_urls = [f.get("download_url") for f in files if f.get("download_url")]
        if not photo_urls:
            logger.warning(f"⚠️ Нет доступных ссылок на фото для сделки {deal_id}")
            return

        logger.info(f"📤 Пытаемся отправить фото в Telegram для сделки {deal_id}")
        try:
            await send_media_group(photo_urls, deal_id=deal_id)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в Telegram: {e}")

        await update_file_links_in_deal(deal_id, photo_urls)
        logger.success(f"✅ Все файлы из папки {folder_id} успешно обработаны для сделки {deal_id}")

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки файлов для сделки {deal_id}: {e}")
        raise