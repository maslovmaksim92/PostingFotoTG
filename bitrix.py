import httpx
from loguru import logger
from config import BITRIX_WEBHOOK
import base64
import io
import re


async def get_files_from_folder(folder_id: int) -> list[dict]:
    url = f"{BITRIX_WEBHOOK}/disk.folder.getchildren"
    payload = {"id": folder_id}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json().get("result", [])

            files = []
            for item in result:
                files.append({
                    "name": item.get("NAME"),
                    "url": item.get("DOWNLOAD_URL"),
                    "id": item.get("ID")
                })
            logger.info(f"✅ Найдено файлов в папке {folder_id}: {len(files)}")
            return files

    except Exception as e:
        logger.error(f"❌ Ошибка при получении файлов из папки {folder_id}: {e}")
        return []


async def get_address_from_deal(deal_id: int) -> str:
    url = f"{BITRIX_WEBHOOK}/crm.deal.get"
    payload = {"id": deal_id}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json().get("result", {})
            address = result.get("UF_CRM_1669561599956", "")
            logger.info(f"📍 Адрес сделки {deal_id}: {address}")
            return address or "Неизвестный адрес"

    except Exception as e:
        logger.error(f"❌ Ошибка получения адреса сделки {deal_id}: {e}")
        return "Неизвестный адрес"


__all__ = [
    "get_files_from_folder",
    "get_address_from_deal"
]