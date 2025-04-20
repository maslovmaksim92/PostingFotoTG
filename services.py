from bitrix import get_deal, get_files_from_folder, attach_files_to_deal
from telegram import send_photos_group, send_video
from gpt import generate_text
from loguru import logger


def process_deal_report(deal_id: int, folder_id: int):
    logger.info(f"Начата обработка сделки {deal_id} и папки {folder_id}")
    files = get_files_from_folder(folder_id)
    photo_files = [f for f in files if f.get("NAME", "").lower().endswith(('.jpg', '.jpeg', '.png'))]
    video_files = [f for f in files if f.get("NAME", "").lower().endswith('.mp4')]

    # Загрузка бинарных данных
    photo_blobs = []
    video_blob = None
    file_ids = []
    for f in photo_files:
        file_id = f["ID"]
        file_ids.append(file_id)
        download_url = f["DOWNLOAD_URL"]
        photo_blobs.append((requests.get(download_url).content))

    if video_files:
        video_blob = requests.get(video_files[0]["DOWNLOAD_URL"]).content

    # Получаем адрес сделки
    deal = get_deal(deal_id)
    address = deal.get("UF_CRM166956159956", "")
    caption = f"📍 {address}\n\n" + generate_text()

    # Отправка в Telegram
    if photo_blobs:
        send_photos_group(photo_blobs, caption=caption)
    if video_blob:
        send_video(video_blob, caption=address)

    # Прикрепление файлов
    if file_ids:
        attach_files_to_deal(deal_id, file_ids)

    logger.success(f"Отчёт по сделке {deal_id} отправлен")