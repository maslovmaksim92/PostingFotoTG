import os
import requests
from typing import List, Dict
from loguru import logger
from dotenv import load_dotenv

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
    return [
        {
            "id": item["ID"],
            "name": item["NAME"],
            "size": item.get("SIZE", 0),
            "download_url": item["DOWNLOAD_URL"]
        }
        for item in result if item["TYPE"] == "file"
    ]

def filter_valid_files(files: List[Dict]) -> List[Dict]:
    filtered = []
    for file in files:
        name = file.get("name", "")
        url = file.get("download_url", "")

        if not name:
            logger.debug(f"⛔️ Пропущен файл без имени: {file}")
            continue
        if not url:
            logger.debug(f"⛔️ Пропущен файл без URL: {file}")
            continue
        if not url.startswith("https://"):
            logger.debug(f"⛔️ Пропущен файл с некорректной ссылкой: {url}")
            continue
        if name.lower().endswith(".tmp") or name.startswith("~"):
            logger.debug(f"⛔️ Пропущен временный файл: {name}")
            continue
        filtered.append(file)
    logger.debug(f"📂 Прошли фильтрацию: {len(filtered)} из {len(files)} файлов")
    return filtered