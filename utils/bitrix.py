import requests
from typing import List, Dict, Optional
from config import settings
from loguru import logger

BASE_URL = f"https://{settings.BITRIX_CLIENT_ID}.bitrix24.ru/rest/1/{settings.BITRIX_CLIENT_SECRET}/"


def _call(method: str, params: Dict) -> dict:
    url = f"{BASE_URL}{method}"
    response = requests.post(url, data=params)
    result = response.json()
    if 'error' in result:
        logger.error(f"Bitrix API error: {result}")
    return result


def get_deal_photos(deal_id: int) -> List[str]:
    """
    Возвращает список URL всех фото, прикреплённых к сделке (по FILE_FIELD_ID).
    """
    result = _call("crm.deal.get", {"id": deal_id})
    deal = result.get("result", {})
    file_ids_raw = deal.get(settings.FILE_FIELD_ID)

    if not file_ids_raw:
        logger.warning(f"Сделка {deal_id}: нет прикреплённых фото")
        return []

    file_ids = file_ids_raw if isinstance(file_ids_raw, list) else [file_ids_raw]

    urls = []
    for file_id in file_ids:
        file_info = _call("disk.file.get", {"id": file_id})
        url = file_info.get("result", {}).get("DOWNLOAD_URL")
        if url:
            urls.append(url)
    return urls


def get_deal_info(deal_id: int) -> Dict[str, Optional[str]]:
    """
    Возвращает адрес и ФИО ответственного из сделки (по FOLDER_FIELD_ID и assigned_by).
    """
    result = _call("crm.deal.get", {"id": deal_id})
    deal = result.get("result", {})

    address = deal.get(settings.FOLDER_FIELD_ID, "Адрес не указан")
    responsible_id = deal.get("ASSIGNED_BY_ID")

    responsible = ""
    if responsible_id:
        user = _call("user.get", {"ID": responsible_id})
        responsible = user.get("result", [{}])[0].get("NAME", "") + " " + user.get("result", [{}])[0].get("LAST_NAME", "")

    return {
        "address": address,
        "responsible": responsible.strip() or None,
    }