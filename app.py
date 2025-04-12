from fastapi import FastAPI, Request
from loguru import logger
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import httpx

load_dotenv()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
BITRIX_FILE_FIELD = "UF_CRM_1740994275251"

app = FastAPI()

class AttachRequest(BaseModel):
    deal_id: int
    folder_id: int


@app.post("/webhook/register_folder")
async def register_folder(data: AttachRequest):
    deal_id = data.deal_id
    folder_id = data.folder_id
    logger.info(f"📥 Получен вебхук: deal={deal_id}, folder={folder_id}")

    async with httpx.AsyncClient() as client:
        # Получить список файлов
        resp = await client.post(
            f"{BITRIX_WEBHOOK}/disk.folder.getchildren",
            json={"id": folder_id}
        )
        children = resp.json().get("result", [])
        file_ids = [f["ID"] for f in children if f["TYPE"] == "file"]

        logger.info(f"🗎 Найдено файлов: {len(file_ids)} — {file_ids}")

        # Обновить сделку — прикрепить файлы
        resp = await client.post(
            f"{BITRIX_WEBHOOK}/crm.deal.update",
            json={
                "id": deal_id,
                "fields": {
                    BITRIX_FILE_FIELD: file_ids
                }
            }
        )

        logger.debug(f"📤 Bitrix response {resp.status_code}: {resp.text}")

        logger.info(f"✅ Файлы успешно прикреплены к сделке {deal_id}")
        return {"status": "ok", "files_attached": len(file_ids)}