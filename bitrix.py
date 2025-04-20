import requests
import os
from loguru import logger

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")


def get_deal(deal_id: int) -> dict:
    url = f"{BITRIX_WEBHOOK}/crm.deal.get.json?id={deal_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json().get("result", {})


def get_files_from_folder(folder_id: int) -> list:
    url = f"{BITRIX_WEBHOOK}/disk.folder.getchildren.json?id={folder_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json().get("result", [])


def attach_files_to_deal(deal_id: int, file_ids: list[int]) -> None:
    url = f"{BITRIX_WEBHOOK}/crm.deal.update.json"
    data = {
        "id": deal_id,
        "fields": {
            "UF_CRM_1740994275251": file_ids
        }
    }
    response = requests.post(url, json=data)
    response.raise_for_status()
    logger.info(f"Файлы {file_ids} прикреплены к сделке {deal_id}")