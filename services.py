from bitrix import get_files_from_folder, attach_media_to_deal, get_address_from_deal, get_deal_fields
from telegram import send_media_group
from utils import fallback_text
from loguru import logger
import httpx
import io
import random
import datetime


async def send_report(deal_id: int, folder_id: int):
    logger.info(f"📦 Начало формирования отчёта для сделки {deal_id}")

    files = await get_files_from_folder(folder_id)
    if not files:
        logger.warning(f"⚠️ Нет файлов для сделки {deal_id}, папка {folder_id}")
        return

    media_group = []
    for file in files:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(file["url"])
                response.raise_for_status()
                media_group.append({
                    "file": io.BytesIO(response.content),
                    "filename": file["name"]
                })
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки файла {file['name']}: {e}")

    if not media_group:
        logger.warning(f"⚠️ Не удалось собрать ни одного файла")
        return

    raw_files = [f["file"].getvalue() for f in media_group]
    bitrix_ready = [
        {"file": io.BytesIO(content), "filename": f["filename"]}
        for content, f in zip(raw_files, media_group)
    ]
    await attach_media_to_deal(deal_id, bitrix_ready)

    # 📍 Адрес
    address = await get_address_from_deal(deal_id)
    header = f"🧹 Уборка подъездов по адресу: *{address}* завершена."

    # 👥 Динамически получаем бригаду из сделки
    deal = await get_deal_fields(deal_id)
    brigada = deal.get("UF_CRM_1741590925181", "[не указана]")
    team_line = f"👷 Уборку провела: *{brigada}*"

    # 🎣 Уникальный байтовый текст на основе времени + ID
    now = datetime.datetime.now().strftime("%H:%M")
    bait = f"💬 Спасибо {brigada} за работу в {now}! Чистота — это стиль жизни. #ЧистоВсё"

    caption = f"{header}\n{team_line}\n\n{bait}"

    await send_media_group(media_group, caption)

    logger.info(f"✅ Отчёт по сделке {deal_id} отправлен и прикреплён")