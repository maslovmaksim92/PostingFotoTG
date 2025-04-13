from fastapi import FastAPI
from pydantic import BaseModel
from loguru import logger
import os
import httpx

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
FIELD_CODE = "UF_CRM_1740994275251"

class FolderPayload(BaseModel):
    deal_id: int
    folder_id: int

@app.post("/webhook/register_folder")
async def register_folder(data: FolderPayload):
    deal_id = data.deal_id
    folder_id = data.folder_id
    logger.info(f"\U0001F4E5 Вебхук получен: deal={deal_id}, folder={folder_id}")

    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BITRIX_WEBHOOK}/disk.folder.getchildren", json={"id": folder_id})
        files = r.json().get("result", [])
        file_ids = [str(f["ID"]) for f in files if f.get("TYPE") == "file"]
        logger.info(f"\U0001F5CE Найдено файлов: {file_ids}")

        attached_ids = []
        for fid in file_ids:
            attach_resp = await client.post(f"{BITRIX_WEBHOOK}/disk.attachedObject.add", json={
                "ENTITY_ID": deal_id,
                "ENTITY_TYPE": "crm_deal",
                "OBJECT_ID": fid
            })
            if attach_resp.status_code == 200:
                attach_id = attach_resp.json().get("result")
                if attach_id:
                    attached_ids.append(str(attach_id))

        logger.info(f"📎 Прикреплено через attachedObject: {attached_ids}")

        if attached_ids:
            update_resp = await client.post(f"{BITRIX_WEBHOOK}/crm.deal.update", json={
                "id": deal_id,
                "fields": {
                    FIELD_CODE: attached_ids
                }
            })
            logger.debug(f"📤 Ответ от Bitrix: {update_resp.status_code} — {update_resp.text}")

    return {"status": "ok", "attached": attached_ids}