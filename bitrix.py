import httpx
from loguru import logger
from config import BITRIX_WEBHOOK
import base64
import io


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
                if 'DOWNLOAD_URL' in item:
                    files.append({
                        "name": item["NAME"],
                        "url": item["DOWNLOAD_URL"]
                    })
            logger.info(f"✅ Найдено файлов в папке {folder_id}: {len(files)}")
            return files

    except Exception as e:
        logger.error(f"❌ Ошибка при получении файлов из папки {folder_id}: {e}")
        return []


# Остальные функции не трогаем: get_address_from_deal, get_deal_fields, attach_media_to_deal

# ... (остальной код остался без изменений, уже в актуальном состоянии) ...