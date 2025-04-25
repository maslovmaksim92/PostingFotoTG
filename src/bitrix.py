import os
import requests
from typing import List, Dict
from loguru import logger
from dotenv import load_dotenv
from urllib.parse import unquote

load_dotenv()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
PHOTO_FIELD_CODE = os.getenv("FILE_FIELD_ID") or "UF_CRM_1740994275251"
FOLDER_FIELD_CODE = os.getenv("FOLDER_FIELD_ID") or "UF_CRM_1743273170850"
ADDRESS_FIELD_CODE = "UF_CRM_1669561599956"

def get_deal_fields(deal_id: int) -> Dict:
    url = f"{BITRIX_WEBHOOK}/crm.deal.get"
    response = requests.post(url, json={"id": deal_id})
    response.raise_for_status()
    return response.json().get("result", {})

def get_address_from_deal(deal_id: int) -> str:
    fields = get_deal_fields(deal_id)
    raw = fields.get(ADDRESS_FIELD_CODE, "")
    return raw.split("|")[0] if "|" in raw else raw

def get_files_from_folder(folder_id: int) -> List[Dict]:
    url = f"{BITRIX_WEBHOOK}/disk.folder.getchildren"
    response = requests.post(url, json={"id": folder_id})
    response.raise_for_status()
    result = response.json().get("result", [])
    valid_files = []
    for item in result:
        if item.get("TYPE") != "file":
            continue
        name = item.get("NAME")
        url = item.get("DOWNLOAD_URL")
        if not name or not url:
            logger.debug(f"⚠️ Пропущен файл без имени или ссылки: {name}")
            continue
        if name.lower().startswith("~") or name.lower() == "thumbs.db":
            logger.debug(f"⚠️ Временный файл пропущен: {name}")
            continue
        valid_files.append({
            "id": item["ID"],
            "name": name,
            "size": item.get("SIZE", 0),
            "download_url": url
        })
    logger.info(f"✅ Найдено файлов в папке {folder_id}: {len(valid_files)}")
    return valid_files

def clean_upload_url(raw_url: str) -> str:
    url = unquote(raw_url)
    if "?" in url:
        url = url.split("?")[0] + "?" + url.split("?")[1].split("|", 1)[0]
    return url.strip()