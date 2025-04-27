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
    return address.replace(",", "").replace("|", "").replace("\\", "").strip()

async def get_files_from_folder(folder_id: int) -> List[Dict]:
    response = await call_bitrix_method("disk.folder.getchildren", {"id": folder_id})
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

async def attach_media_to_deal(deal_id: int, files: List[Dict]) -> List[int]:
    logger.info(f"\ud83d\udccc \u041f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0435\u043d\u0438\u0435 \u0444\u0430\u0439\u043b\u043e\u0432 \u043d\u0430\u043f\u0440\u044f\u043c\u0443\u044e \u043f\u043e ID \u043a \u0441\u0434\u0435\u043b\u043a\u0435 {deal_id}")
    if not files:
        logger.warning(f"\u26a0\ufe0f \u041d\u0435\u0442 \u0444\u0430\u0439\u043b\u043e\u0432 \u0434\u043b\u044f \u043f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0435\u043d\u0438\u044f \u0432 \u0441\u0434\u0435\u043b\u043a\u0435 {deal_id}")
        return []

    file_ids = [int(file["id"]) for file in files if file.get("id")]

    if not file_ids:
        logger.warning(f"\u26a0\ufe0f \u041d\u0435\u0442 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0445 ID \u0444\u0430\u0439\u043b\u043e\u0432 \u0434\u043b\u044f \u043f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0435\u043d\u0438\u044f \u043a \u0441\u0434\u0435\u043b\u043a\u0435 {deal_id}")
        return []

    payload = {"id": deal_id, "fields": {PHOTO_FIELD_CODE: file_ids}}

    async def check_files_attached() -> bool:
        try:
            deal = await get_deal_fields(deal_id)
            attached = deal.get(PHOTO_FIELD_CODE, [])
            return bool(attached)
        except Exception as e:
            logger.error(f"\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 \u0444\u0430\u0439\u043b\u043e\u0432: {e}")
            return False

    try:
        await call_bitrix_method("crm.deal.update", payload)
        await asyncio.sleep(2)

        if not await check_files_attached():
            logger.warning(f"\u26a0\ufe0f \u041f\u0435\u0440\u0432\u0430\u044f \u043f\u043e\u043f\u044b\u0442\u043a\u0430 \u043d\u0435\u0443\u0434\u0430\u0447\u043d\u0430, \u043f\u0440\u043e\u0431\u0443\u0435\u043c \u043f\u043e\u0432\u0442\u043e\u0440\u043d\u043e...")
            await asyncio.sleep(3)
            await call_bitrix_method("crm.deal.update", payload)
            await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438\u043a\u0440\u0435\u043f\u043b\u0435\u043d\u0438\u044f \u0444\u0430\u0439\u043b\u043e\u0432: {e}")

    return file_ids

async def update_file_links_in_deal(deal_id: int, links: List[str]):
    if not links:
        logger.warning(f"\u26a0\ufe0f \u041d\u0435\u0442 \u0441\u0441\u044b\u043b\u043e\u043a \u0434\u043b\u044f \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f \u0432 \u0441\u0434\u0435\u043b\u043a\u0435 {deal_id}")
        return

    payload = {
        "id": deal_id,
        "fields": {
            FILE_LINKS_FIELD_CODE: links
        }
    }
    await call_bitrix_method("crm.deal.update", payload)
    logger.success(f"✅ Ссылки успешно добавлены в сделку {deal_id}")