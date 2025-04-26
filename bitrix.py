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
FILE_LINKS_FIELD_CODE = "UF_CRM_1745671890168"

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
    logger.info(f"📎 Прикрепление файлов к сделке {deal_id} через ID файлов (без скачивания)")
    file_ids = []
    download_urls = []

    if not files:
        logger.warning(f"⚠️ Нет файлов для прикрепления в сделке {deal_id}")
        return []

    logger.debug(f"📋 Список файлов к прикреплению: {[file['name'] for file in files]}")

    for file in files:
        file_id = file.get("id")
        download_url = file.get("download_url")
        if file_id:
            file_ids.append(int(file_id))
        if download_url:
            download_urls.append(download_url)

    if file_ids:
        payload = {"id": deal_id, "fields": {PHOTO_FIELD_CODE: file_ids}}
        update_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
        logger.debug(f"➡️ Обновляем сделку {deal_id} прикреплением файлов: {file_ids}")
        try:
            update_resp = requests.post(update_url, json=payload)
            update_resp.raise_for_status()
            logger.info(f"✅ Файлы через ID прикреплены к сделке {deal_id}: {file_ids}")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления сделки при прикреплении файлов: {e}")

    if download_urls:
        payload_links = {
            "id": deal_id,
            "fields": {
                FILE_LINKS_FIELD_CODE: "\n".join(download_urls)
            }
        }
        update_links_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
        try:
            links_resp = requests.post(update_links_url, json=payload_links)
            links_resp.raise_for_status()
            logger.info(f"🔗 Ссылки на файлы сохранены в сделке {deal_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения ссылок на файлы: {e}")

    return file_ids