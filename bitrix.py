import os
import time
import requests
from typing import List, Dict
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from your_app_onrender_com__jit_plugin import bitrixCall  # ✅ Правильный импорт

load_dotenv()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
PHOTO_FIELD_CODE = os.getenv("FILE_FIELD_ID") or "UF_CRM_1740994275251"
FOLDER_FIELD_CODE = os.getenv("FOLDER_FIELD_ID") or "UF_CRM_1743273170850"
ADDRESS_FIELD_CODE = "UF_CRM_1669561599956"
FILE_LINKS_FIELD_CODE = "UF_CRM_1745671890168"

def get_deal_fields(deal_id: int) -> Dict:
    response = bitrixCall({"method": f"crm.deal.get?ID={deal_id}"})
    return response.get("result", {})

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
    response = bitrixCall({"method": f"disk.folder.getchildren?id={folder_id}"})
    result = response.get("result", [])
    logger.debug(f"\ud83d\udd0d \u041d\u0430\u0439\u0434\u0435\u043d\u043e \u0444\u0430\u0439\u043b\u043e\u0432 \u0432 \u043f\u0430\u043f\u043a\u0435 {folder_id}: {len(result)} \u0444\u0430\u0439\u043b\u043e\u0432")
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
    logger.info(f"\ud83d\udccE \u041f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0435\u043d\u0438\u0435 \u0444\u0430\u0439\u043b\u043e\u0432 \u043d\u0430\u043f\u0440\u044f\u043c\u0443\u044e \u043f\u043e ID \u043a \u0441\u0434\u0435\u043b\u043a\u0435 {deal_id}")

    if not files:
        logger.warning(f"\u26a0\ufe0f \u041d\u0435\u0442 \u0444\u0430\u0439\u043b\u043e\u0432 \u0434\u043b\u044f \u043f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0435\u043d\u0438\u044f \u0432 \u0441\u0434\u0435\u043b\u043a\u0435 {deal_id}")
        return []

    file_ids = [int(file["id"]) for file in files if file.get("id")]

    if not file_ids:
        logger.warning(f"\u26a0\ufe0f \u041d\u0435\u0442 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0445 ID \u0444\u0430\u0439\u043b\u043e\u0432 \u0434\u043b\u044f \u043f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0435\u043d\u0438\u044f \u043a \u0441\u0434\u0435\u043b\u043a\u0435 {deal_id}")
        return []

    payload = {
        "id": deal_id,
        "fields": {
            PHOTO_FIELD_CODE: file_ids
        }
    }

    def check_files_attached() -> bool:
        try:
            deal = get_deal_fields(deal_id)
            attached = deal.get(PHOTO_FIELD_CODE, [])
            logger.debug(f"\ud83d\udccb \u0421\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 \u0444\u0430\u0439\u043b\u043e\u0432 \u0432 \u0441\u0434\u0435\u043b\u043a\u0435 {deal_id}: {attached}")
            return bool(attached)
        except Exception as e:
            logger.error(f"\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0435 \u043f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0451\u043d\u043d\u044b\u0445 \u0444\u0430\u0439\u043b\u043e\u0432: {e}")
            return False

    try:
        bitrixCall({"method": "crm.deal.update", "params": payload})
        logger.info(f"\u2705 \u0424\u0430\u0439\u043b\u044b \u043f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0435\u043d\u044b \u043a \u0441\u0434\u0435\u043b\u043a\u0435 {deal_id}: {file_ids}")
        time.sleep(2)

        if not check_files_attached():
            logger.warning(f"\u26a0\ufe0f \u041f\u043e\u0441\u043b\u0435 \u043f\u0435\u0440\u0432\u043e\u0439 \u043f\u043e\u043f\u044b\u0442\u043a\u0438 \u0444\u0430\u0439\u043b\u044b \u043d\u0435 \u043f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0435\u043d\u044b, \u043f\u0440\u043e\u0431\u0443\u0435\u043c \u043f\u043e\u0432\u0442\u043e\u0440\u043d\u043e...")
            time.sleep(3)
            bitrixCall({"method": "crm.deal.update", "params": payload})
            time.sleep(2)
            if check_files_attached():
                logger.success(f"\u2705 \u041f\u043e\u0441\u043b\u0435 \u043f\u043e\u0432\u0442\u043e\u0440\u0430 \u0444\u0430\u0439\u043b\u044b \u043f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0435\u043d\u044b \u043a \u0441\u0434\u0435\u043b\u043a\u0435 {deal_id}")
            else:
                logger.error(f"\u274c \u041f\u043e\u0441\u043b\u0435 \u043f\u043e\u0432\u0442\u043e\u0440\u0430 \u0444\u0430\u0439\u043b\u044b \u0432\u0441\u0451 \u0435\u0449\u0451 \u043d\u0435 \u043f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0435\u043d\u044b \u043a \u0441\u0434\u0435\u043b\u043a\u0435 {deal_id}")
    except Exception as e:
        logger.error(f"\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u043f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0435\u043d\u0438\u0438 \u0444\u0430\u0439\u043b\u043e\u0432 \u043a \u0441\u0434\u0435\u043b\u043a\u0435 {deal_id}: {e}")

    return file_ids

def update_file_links_in_deal(deal_id: int, files: List[Dict]):
    links = []
    for file in files:
        url = file.get("download_url")
        if url:
            url = url.replace("&auth=", "?auth=")
            links.append(url)

    payload = {
        "id": deal_id,
        "fields": {
            FILE_LINKS_FIELD_CODE: links
        }
    }

    try:
        bitrixCall({"method": "crm.deal.update", "params": payload})
        logger.success(f"\ud83d\udd17 \u0421\u0441\u044b\u043b\u043a\u0438 \u043d\u0430 \u0444\u0430\u0439\u043b\u044b \u0432\u0441\u0442\u0430\u0432\u043b\u0435\u043d\u044b \u0432 \u0441\u0434\u0435\u043b\u043a\u0443 {deal_id}")
    except Exception as e:
        logger.error(f"\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u0432\u0441\u0442\u0430\u0432\u043a\u0435 \u0441\u0441\u044b\u043b\u043e\u043a \u0432 \u0441\u0434\u0435\u043b\u043a\u0443 {deal_id}: {e}")