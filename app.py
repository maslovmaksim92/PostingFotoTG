from fastapi import FastAPI, Request
from pydantic import BaseModel
from loguru import logger
import httpx
import os

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
FIELD_CODE = "UF_CRM_1740994275251"


class RegisterFolderPayload(BaseModel):
    deal_id: int
    folder_id: int


@app.post("/webhook/register_folder")
async def register_folder(payload: RegisterFolderPayload):
    deal_id = payload.deal_id
    folder_id = payload.folder_id
    logger.info(f"\U0001F4E5 Получен вебхук: deal={deal_id}, folder={folder_id}")

    async with httpx.AsyncClient() as client:
        # Получение списка файлов
        r = await client.post(f"{BITRIX_WEBHOOK}/disk.folder.getchildren", json={"id": folder_id})
        children = r.json().get("result", [])
        file_ids = [str(file["ID"]) for file in children if file["TYPE"] == "file"]
        logger.info(f"\U0001F5CE Найдено файлов: {len(file_ids)} — {file_ids}")

        # Прикрепляем файлы к сделке
        attached = []
        for fid in file_ids:
            attach_resp = await client.post(f"{BITRIX_WEBHOOK}/disk.attachedObject.add", json={
                "ENTITY_ID": deal_id,
                "ENTITY_TYPE": "crm_deal",
                "OBJECT_ID": fid
            })
            if attach_resp.status_code == 200:
                attached.append(fid)

        logger.info(f"\u2705 Прикреплено файлов: {len(attached)}")

        # Обновляем сделку
        update = await client.post(f"{BITRIX_WEBHOOK}/crm.deal.update", json={
            "id": deal_id,
            "fields": {
                FIELD_CODE: attached
            }
        })

        logger.debug(f"\U0001F4E4 Bitrix response {update.status_code}: {update.text}")

    logger.info(f"\u2705 Файлы успешно прикреплены к сделке {deal_id}")
    return {"status": "ok", "files_attached": len(attached)}