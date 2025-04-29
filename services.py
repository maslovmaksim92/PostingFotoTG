from bitrix import get_files_from_folder, attach_media_to_deal, update_file_links_in_deal, check_files_attached
from telegram import send_media_group
from loguru import logger
import asyncio

async def upload_folder_to_deal(deal_id: int, folder_id: int):
    try:
        # 1. Получаем файлы из папки
        files = await get_files_from_folder(folder_id)
        if not files:
            logger.warning(f"⚠️ Нет файлов в папке {folder_id} для сделки {deal_id}")
            return

        # 2. Прикрепляем файлы по их ID
        attached_ids = await attach_media_to_deal(deal_id, files)
        if attached_ids:
            logger.info(f"💎 Файлы прикреплены по ID: {attached_ids}")
        else:
            logger.warning(f"⚠️ Файлы не прикрепились по ID, возможно потребуется доп. обработка")

        # 3. Дополнительная проверка прикрепления
        logger.info(f"⏳ Ждём 2 секунды для проверки состояния файлов...")
        await asyncio.sleep(2)

        is_attached = await check_files_attached(deal_id)
        if not is_attached:
            logger.warning(f"⚠️ Файлы всё ещё не прикреплены к сделке {deal_id}, повторная попытка...")
            await asyncio.sleep(2)
            attached_ids = await attach_media_to_deal(deal_id, files)
            await asyncio.sleep(2)

            if await check_files_attached(deal_id):
                logger.success(f"✅ После повтора файлы прикреплены к сделке {deal_id}")
            else:
                logger.error(f"❌ После повтора файлы всё ещё не прикреплены к сделке {deal_id}")

        # 4. Подготавливаем ссылки на фото
        photo_urls = []
        for f in files:
            url = f.get("download_url")
            if url:
                url = url.replace("&auth=", "?auth=") if "&auth=" in url else url
                photo_urls.append(url)

        if not photo_urls:
            logger.warning(f"⚠️ Нет доступных ссылок на фото для сделки {deal_id}")
            return

        # 5. Отправляем фото в Telegram
        logger.info(f"📤 Пытаемся отправить фото в Telegram для сделки {deal_id}")
        try:
            await send_media_group(photo_urls, "")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки фото в Telegram: {e}")

        # 6. Сохраняем ссылки на фото в сделке
        await update_file_links_in_deal(deal_id, photo_urls)
        logger.success(f"✅ Ссылки на фото успешно сохранены в сделке {deal_id}")

        logger.success(f"✅ Все файлы из папки {folder_id} успешно обработаны для сделки {deal_id}")

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки файлов для сделки {deal_id}: {e}")
        raise
