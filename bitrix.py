import os
import requests
from typing import List, Dict
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
PHOTO_FIELD_CODE = os.getenv("FILE_FIELD_ID") or "UF_CRM_1740994275251"
FOLDER_FIELD_CODE = os.getenv("FOLDER_FIELD_ID") or "UF_CRM_1743273170850"
ADDRESS_FIELD_CODE = "UF_CRM_1669561599956"
FILE_LINKS_FIELD_CODE = "UF_CRM_1745671890168"


def get_deal_fields(deal_id: int) -> Dict:
    url = f"{BITRIX_WEBHOOK}/crm.deal.get"
    response = requests.post(url, json={"id": deal_id})
    response.raise_for_status()
    return response.json().get("result", {})


def get_address_from_deal(deal_id: int) -> str:
    fields = get_deal_fields(deal_id)
    raw = fields.get(ADDRESS_FIELD_CODE, "")
    if "|" in raw:
        address = raw.split("|")[0]
    else:
        address = raw
    address = address.replace(",", "").replace("|", "").replace("\\", "").strip()
    return address


def get_files_from_folder(folder_id: int) -> List[Dict]:
    url = f"{BITRIX_WEBHOOK}/disk.folder.getchildren"
    response = requests.post(url, json={"id": folder_id})
    response.raise_for_status()
    result = response.json().get("result", [])
    logger.debug(f"🔍 Найдено файлов в папке {folder_id}: {len(result)} файлов")
    return [
        {
            "id": item["ID"],
            "name": item["NAME"],
            "size": item.get("SIZE", 0),
            "download_url": item.get("DOWNLOAD_URL")
        }
        for item in result if item["TYPE"] == "file"
    ]


def attach_media_to_deal(deal_id: int, files: List[Dict]) -> List[int]:
    logger.info(f"📎 Прикрепление файлов напрямую по ID к сделке {deal_id}")

    if not files:
        logger.warning(f"⚠️ Нет файлов для прикрепления в сделке {deal_id}")
        return []

    file_ids = [int(file["id"]) for file in files if file.get("id")]

    if not file_ids:
        logger.warning(f"⚠️ Нет действительных ID файлов для прикрепления к сделке {deal_id}")
        return []

    payload = {
        "id": deal_id,
        "fields": {
            PHOTO_FIELD_CODE: file_ids
        }
    }

    update_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
    try:
        update_resp = requests.post(update_url, json=payload)
        update_resp.raise_for_status()
        logger.info(f"✅ Файлы успешно прикреплены к сделке {deal_id}: {file_ids}")
    except Exception as e:
        logger.error(f"❌ Ошибка при прикреплении файлов к сделке {deal_id}: {e}")

    return file_ids