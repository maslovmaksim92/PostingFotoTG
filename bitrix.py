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


async def attach_media_to_deal(deal_id: int, media_group: list[dict], folder_id: int) -> None:
    upload_url = f"{BITRIX_WEBHOOK}/disk.folder.uploadfile"
    bind_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
    field_code = "UF_CRM_1740994275251"

    uploaded_ids = []
    for item in media_group:
        try:
            content = item["file"].getvalue()
            encoded_file = base64.b64encode(content).decode("utf-8")
            filename = item["filename"]
            safe_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)

            upload_payload = {
                "id": folder_id,
                "data": {"NAME": safe_filename, "CREATED_BY": 1},
                "fileContent": [safe_filename, encoded_file]
            }

            logger.debug(f"📤 Upload payload: {safe_filename} (size: {len(encoded_file)} bytes)")

            async with httpx.AsyncClient() as client:
                upload_resp = await client.post(upload_url, json=upload_payload)
                upload_resp.raise_for_status()
                upload_id = upload_resp.json().get("result", {}).get("ID")
                if upload_id:
                    uploaded_ids.append(upload_id)

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки файла в Bitrix: {e}")

    if uploaded_ids:
        try:
            bind_payload = {
                "id": deal_id,
                "fields": {
                    field_code: uploaded_ids
                }
            }
            logger.debug(f"➡️ CRM PAYLOAD (uploadfile): {bind_payload}")
            async with httpx.AsyncClient() as client:
                update_resp = await client.post(bind_url, json=bind_payload)
                update_resp.raise_for_status()
                logger.debug(f"✅ Ответ от Bitrix: {update_resp.json()}")
                logger.info(f"📎 Прикреплены файлы к сделке {deal_id}: {uploaded_ids}")
        except Exception as e:
            logger.error(f"❌ Ошибка привязки файлов к сделке (uploadfile): {e}")


__all__ = [
    "get_files_from_folder",
    "attach_media_to_deal"
]