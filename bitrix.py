import httpx
from loguru import logger
from config import BITRIX_WEBHOOK
import base64

# ... существующие функции сохранены ...


async def attach_media_to_deal(deal_id: int, media_group: list[dict]) -> None:
    upload_url = f"{BITRIX_WEBHOOK}/disk.folder.uploadfile"
    bind_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
    field_code = "UF_CRM_1740994275251"

    uploaded_ids = []

    for item in media_group:
        try:
            content = item["file"].getvalue()
            encoded_file = base64.b64encode(content).decode("utf-8")
            filename = item["filename"]

            # Шаг 1: Загрузим файл во временную папку
            upload_payload = {
                "data": {"NAME": filename, "CREATED_BY": 1},
                "fileContent": [filename, encoded_file]
            }

            async with httpx.AsyncClient() as client:
                upload_resp = await client.post(upload_url, json=upload_payload)
                upload_resp.raise_for_status()
                upload_id = upload_resp.json().get("result", {}).get("ID")
                if upload_id:
                    uploaded_ids.append(upload_id)

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки файла в Bitrix: {e}")

    # Шаг 2: Обновим сделку, добавив ID файлов в поле UF
    if uploaded_ids:
        try:
            bind_payload = {
                "id": deal_id,
                "fields": {
                    field_code: uploaded_ids
                }
            }
            async with httpx.AsyncClient() as client:
                update_resp = await client.post(bind_url, json=bind_payload)
                update_resp.raise_for_status()
                logger.info(f"📎 Прикреплены файлы к сделке {deal_id}: {uploaded_ids}")
        except Exception as e:
            logger.error(f"❌ Ошибка привязки файлов к сделке: {e}")