import os
import time
import httpx
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

async def call_bitrix_method(method: str, params: dict = None):
    if params is None:
        params = {}

    if not BITRIX_WEBHOOK:
        raise ValueError("BITRIX_WEBHOOK is not set in environment variables")

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{BITRIX_WEBHOOK}/{method}", json=params)
        response.raise_for_status()
        return response.json()

def get_deal_fields(deal_id: int) -> Dict:
    import asyncio
    return asyncio.run(call_bitrix_method(f"crm.deal.get", {"ID": deal_id})).get("result", {})

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
    import asyncio
    result = asyncio.run(call_bitrix_method(f"disk.folder.getchildren", {"id": folder_id})).get("result", [])
    logger.debug(f"\U0001F50D Найдено файлов в папке {folder_id}: {len(result)} файлов")
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
    logger.info(f"\U0001F4CE Прикрепление файлов напрямую по ID к сделке {deal_id}")

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

    def check_files_attached() -> bool:
        try:
            deal = get_deal_fields(deal_id)
            attached = deal.get(PHOTO_FIELD_CODE, [])
            logger.debug(f"\U0001F4CB Состояние файлов в сделке {deal_id}: {attached}")
            return bool(attached)
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке прикрепленных файлов: {e}")
            return False

    try:
        import asyncio
        asyncio.run(call_bitrix_method("crm.deal.update", payload))
        logger.info(f"✅ Файлы прикреплены к сделке {deal_id}: {file_ids}")

        logger.info("⏳ Ждём 2 секунды перед проверкой состояния...")
        time.sleep(2)

        if not check_files_attached():
            logger.warning(f"⚠️ После первой попытки файлы не прикреплены, пробуем повторно...")
            time.sleep(3)
            asyncio.run(call_bitrix_method("crm.deal.update", payload))
            time.sleep(2)
            if check_files_attached():
                logger.success(f"✅ После повтора файлы прикреплены к сделке {deal_id}")
            else:
                logger.error(f"❌ После повтора файлы всё ещё не прикреплены к сделке {deal_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка при прикреплении файлов к сделке {deal_id}: {e}")

    return file_ids

def update_file_links_in_deal(deal_id: int, links: List[str]) -> None:
    logger.info(f"✍️ Обновление ссылки на файлы в сделке {deal_id}")
    fields = {FILE_LINKS_FIELD_CODE: links}
    import asyncio
    asyncio.run(call_bitrix_method("crm.deal.update", {"id": deal_id, "fields": fields}))
    logger.success(f"✅ Ссылки добавлены в карточку сделки {deal_id}")