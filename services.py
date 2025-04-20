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

    bitrix_group = files.copy()  # сохраняем ID для прикрепления
    media_group = []
    for file in files:
        if not file.get("url"):
            continue
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

    await attach_media_to_deal(deal_id, bitrix_group, folder_id)

    address = await get_address_from_deal(deal_id)
    header = f"🧹 Уборка подъездов по адресу: *{address}* завершена."

    deal = await get_deal_fields(deal_id)
    brigada = deal.get("UF_CRM_1741590925181", "[не указана]")
    team_line = f"👷 Уборку провела: *{brigada}*"

    now = datetime.datetime.now().strftime("%H:%M")
    bait = f"💬 Спасибо {brigada} за работу в {now}! Чистота — это стиль жизни. #ЧистоВсё"
    caption = f"{header}\n{team_line}\n\n{bait}"

    # Разбиваем на блоки по 10
    for i in range(0, len(media_group), 10):
        group = media_group[i:i + 10]
        cap = caption if i == 0 else None
        await send_media_group(group, cap)

    logger.info(f"✅ Отчёт по сделке {deal_id} отправлен и прикреплён")