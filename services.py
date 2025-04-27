from bitrix import get_files_from_folder, attach_media_to_deal, update_file_links_in_deal
from telegram import send_media_group
from loguru import logger
import asyncio


def upload_folder_to_deal(deal_id: int, folder_id: int):
    try:
        files = get_files_from_folder(folder_id)
        if not files:
            logger.warning(f"⚠️ Нет файлов в папке {folder_id} для сделки {deal_id}")
            return

        attached_ids = attach_media_to_deal(deal_id, files)

        if attached_ids:
            logger.info(f"📎 Файлы прикреплены по ID: {attached_ids}")
        else:
            logger.warning(f"⚠️ Файлы не прикрепились по ID, возможно потребуется доп. обработка")

        # Подготовка ссылок на файлы
        photo_urls = []
        for f in files:
            url = f.get("download_url")
            if url and "&auth=" in url:
                url = url.replace("&auth=", "?auth=")
            if url:
                photo_urls.append(url)

        if not photo_urls:
            logger.warning(f"⚠️ Нет ссылок на фото для сделки {deal_id}")
            return

        logger.info(f"📤 Пытаемся отправить фото в Telegram для сделки {deal_id}")
        try:
            asyncio.create_task(send_media_group(photo_urls, ""))
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в Telegram: {e}")

        # Сохраняем ссылки в карточку сделки
        update_file_links_in_deal(deal_id, photo_urls)
        logger.success(f"✅ Ссылки на фото сохранены в сделке {deal_id}")

        logger.success(f"✅ Файлы из папки {folder_id} прикреплены и отправлены к сделке {deal_id}")

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки файлов для сделки {deal_id}: {e}")
        raise