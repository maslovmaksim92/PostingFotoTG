import os
import httpx
import asyncio
from typing import List, Dict
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
PHOTO_FIELD_CODE = os.getenv("FILE_FIELD_ID") or "UF_CRM_1740994275251"
FOLDER_FIELD_CODE = os.getenv("FOLDER_FIELD_ID") or "UF_CRM_1743273170850"
ADDRESS_FIELD_CODE = "UF_CRM_1669561599956"
FILE_LINKS_FIELD_CODE = "UF_CRM_1745671890168"

async def call_bitrix_method(method: str, params: dict = None) -> dict:
    url = f"{BITRIX_WEBHOOK}/{method}"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=params or {})
        response.raise_for_status()
        return response.json()

async def get_deal_fields(deal_id: int) -> Dict:
    response = await call_bitrix_method("crm.deal.get", {"ID": deal_id})
    return response.get("result", {})

async def get_address_from_deal(deal_id: int) -> str:
    fields = await get_deal_fields(deal_id)
    raw = fields.get(ADDRESS_FIELD_CODE, "")
    if "|" in raw:
        address = raw.split("|")[0]
    else:
        address = raw
    address = address.replace(",", "").replace("|", "").replace("\\", "").strip()
    return address

async def get_files_from_folder(folder_id: int) -> List[Dict]:
    response = await call_bitrix_method("disk.folder.getchildren", {"id": folder_id})
    result = response.get("result", [])
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

async def attach_media_to_deal(deal_id: int, files: List[Dict]) -> List[int]:
    logger.info(f"📎 Прикрепление файлов напрямую по ID к сделке {deal_id}")
    if not files:
        logger.warning(f"⚠️ Нет файлов для прикрепления в сделке {deal_id}")
        return []

    file_ids = [int(file["id"]) for file in files if file.get("id")]

    if not file_ids:
        logger.warning(f"⚠️ Нет действительных ID файлов для прикрепления к сделке {deal_id}")
        return []

    payload = {"id": deal_id, "fields": {PHOTO_FIELD_CODE: file_ids}}

    async def check_files_attached() -> bool:
        try:
            deal = await get_deal_fields(deal_id)
            attached = deal.get(PHOTO_FIELD_CODE, [])
            logger.debug(f"📋 Состояние файлов в сделке {deal_id}: {attached}")
            return bool(attached)
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке прикрепленных файлов: {e}")
            return False

    try:
        await call_bitrix_method("crm.deal.update", payload)
        logger.info(f"✅ Файлы прикреплены к сделке {deal_id}: {file_ids}")

        logger.info("⏳ Ждём 2 секунды перед проверкой состояния...")
        await asyncio.sleep(2)

        if not await check_files_attached():
            logger.warning(f"⚠️ После первой попытки файлы не прикреплены, пробуем повторно...")
            await asyncio.sleep(3)
            await call_bitrix_method("crm.deal.update", payload)
            await asyncio.sleep(2)
            if await check_files_attached():
                logger.success(f"✅ После повтора файлы прикреплены к сделке {deal_id}")
            else:
                logger.error(f"❌ После повтора файлы всё ещё не прикреплены к сделке {deal_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка при прикреплении файлов к сделке {deal_id}: {e}")

    return file_ids

async def update_file_links_in_deal(deal_id: int, links: List[str]):
    if not links:
        logger.warning(f"⚠️ Нет ссылок для обновления в сделке {deal_id}")
        return

    payload = {
        "id": deal_id,
        "fields": {
            FILE_LINKS_FIELD_CODE: links
        }
    }
    await call_bitrix_method("crm.deal.update", payload)
    logger.success(f"✅ Ссылки успешно добавлены в сделку {deal_id}")
