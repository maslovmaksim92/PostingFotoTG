import requests
from config import settings
from loguru import logger

BASE_URL = "https://local.67e85c29746cb1.58287098.bitrix24.ru/rest/1/zNeKebH9555gmzHvcDdCbicZ8fDkGY8vwzPxYOd3Vhfv68vgRn/"


def get_deal_info(deal_id: int) -> dict:
    try:
        res = requests.post(
            f"{BASE_URL}crm.deal.get",
            data={"id": deal_id},
            timeout=10,
        )
        data = res.json().get("result", {})
        logger.info(f"🔎 Информация о сделке {deal_id} получена: {data}")
        return data
    except Exception as e:
        logger.error(f"❌ Ошибка при получении сделки {deal_id}: {e}")
        return {}


def get_deal_photos(deal: dict) -> list[str]:
    photo_ids = deal.get(settings.FILE_FIELD_ID, [])
    if isinstance(photo_ids, str):
        photo_ids = [photo_ids]

    photo_urls = []
    for file_id in photo_ids:
        try:
            res = requests.post(
                f"{BASE_URL}disk.file.get",
                data={"id": file_id},
                timeout=10,
            )
            url = res.json().get("result", {}).get("DOWNLOAD_URL")
            if url:
                photo_urls.append(url)
        except Exception as e:
            logger.error(f"❌ Ошибка при получении фото {file_id}: {e}")

    return photo_urls