from fastapi import FastAPI, Request
from pydantic import BaseModel
from loguru import logger
import httpx
import os

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
BITRIX_FIELD_FILE = "UF_CRM_1740994275251"

class FolderRegisterPayload(BaseModel):
    deal_id: int
    folder_id: int

@app.post("/webhook/register_folder")
async def register_folder(payload: FolderRegisterPayload):
    logger.info(f"\U0001F4E5 Получен вебхук: deal={payload.deal_id}, folder={payload.folder_id}")

    async with httpx.AsyncClient() as client:
        # Получение списка файлов в папке
        disk_url = f"{BITRIX_WEBHOOK}/disk.folder.getchildren"
        r = await client.post(disk_url, json={"id": payload.folder_id})
        r.raise_for_status()
        files = r.json().get("result", [])
        file_ids = [f["ID"] for f in files if f.get("ID")]
        logger.info(f"\U0001F5CE Найдено файлов: {len(file_ids)} — {file_ids}")

        if not file_ids:
            return {"status": "error", "message": "Файлы не найдены"}

        # Отправка файлов в сделку
        update_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
        data = {
            "id": payload.deal_id,
            "fields": {
                BITRIX_FIELD_FILE: file_ids
            }
        }
        resp = await client.post(update_url, json=data)
        resp.raise_for_status()
        logger.info(f"\u2705 Файлы успешно прикреплены к сделке {payload.deal_id}")

        return {"status": "ok", "attached": len(file_ids)}