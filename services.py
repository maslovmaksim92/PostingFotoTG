from bitrix import get_files_from_folder, attach_media_to_deal, get_address_from_deal
from telegram import send_media_group
from gpt import generate_caption
from utils import fallback_text
from loguru import logger
import httpx
import io
import random


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

    # Прикрепляем к сделке
    raw_files = [f["file"].getvalue() for f in media_group]
    bitrix_ready = [
        {"file": io.BytesIO(content), "filename": f["filename"]}
        for content, f in zip(raw_files, media_group)
    ]
    await attach_media_to_deal(deal_id, bitrix_ready)

    # 📍 1. Получаем адрес
    address = await get_address_from_deal(deal_id)
    header = f"🧹 Уборка подъездов по адресу: *{address}* завершена."

    # 👥 2. Ответственный/бригада (заглушка, можно заменить)
    brigada = "Бригада №3"
    team_line = f"👷 Уборку провела: *{brigada}*"

    # 🎣 3. Байтовый текст (рандомно из списка)
    bait_list = [
        "Спасибо за чистоту и уют, которые вы создаёте!",
        "Ваш отзыв — лучшая награда 🧽",
        "Чисто не там, где убирают, а там, где ценят!",
        "Подъезд блестит — настроение растёт!",
        "Вы бы видели, как мы старались! 😅"
    ]
    bait = random.choice(bait_list)

    caption = f"{header}\n{team_line}\n\n{bait}"

    await send_media_group(media_group, caption)

    logger.info(f"✅ Отчёт по сделке {deal_id} отправлен и прикреплён")