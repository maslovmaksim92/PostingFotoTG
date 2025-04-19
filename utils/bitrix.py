import base64
import httpx
from loguru import logger
from config import settings


async def fetch_folder_files(folder_id: int) -> list[dict]:
    url = f"{settings.BITRIX_WEBHOOK}/disk.folder.getchildren"
    logger.info(f"📂 Получение содержимого папки Bitrix ID={folder_id}")

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={"id": folder_id})
        files = resp.json().get("result", [])
        return [f for f in files if f.get("DOWNLOAD_URL")]


async def download_files(file_list: list[dict]) -> list[dict]:
    results = []
    async with httpx.AsyncClient() as client:
        for f in file_list:
            name = f.get("NAME", "file.jpg")
            url = f.get("DOWNLOAD_URL")
            if not url:
                continue

            logger.info(f"⬇️ Скачивание файла: {name}")
            resp = await client.get(url)
            if resp.status_code == 200:
                content = base64.b64encode(resp.content).decode("utf-8")
                results.append({"fileData": [name, content]})
            else:
                logger.warning(f"❌ Ошибка загрузки {name}: {resp.status_code}")
    return results


async def update_deal_files(deal_id: int, file_data: list[dict]) -> None:
    logger.info(f"📤 Обновление сделки {deal_id} с {len(file_data)} файлами")
    url = f"{settings.BITRIX_WEBHOOK}/crm.deal.update"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={
            "id": deal_id,
            "fields": {
                settings.FILE_FIELD_ID: file_data
            }
        })
        logger.debug(f"📦 Ответ Bitrix: {resp.text}")