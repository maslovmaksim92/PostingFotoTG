import os
import logging
from fastapi import FastAPI, Request
from pydantic import BaseModel
from loguru import logger
from dotenv import load_dotenv

from utils.bitrix import Bitrix

load_dotenv()

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")


class FolderPayload(BaseModel):
    deal_id: int
    folder_id: int


@app.post("/webhook/register_folder")
async def register_folder(payload: FolderPayload):
    deal_id = payload.deal_id
    folder_id = payload.folder_id
    logger.info(f"\U0001F4E5 Получен вебхук: deal={deal_id}, folder={folder_id}")

    bitrix = Bitrix(BITRIX_WEBHOOK)

    # Получаем список файлов
    children = await bitrix.call("disk.folder.getchildren", {"id": folder_id})
    file_ids = [f["ID"] for f in children.get("result", []) if f.get("ID")]
    logger.info(f"\U0001F4CE Найдено файлов: {len(file_ids)} — {file_ids}")

    attached_ids = []
    for fid in file_ids:
        resp = await bitrix.call("disk.attachedObject.add", {
            "ENTITY_TYPE": "crm_deal",
            "ENTITY_ID": deal_id,
            "OBJECT_ID": fid
        })
        if isinstance(resp, dict) and resp.get("result"):
            attached_ids.append(resp["result"])

    # Обновляем сделку, если есть что прикрепить
    if attached_ids:
        update = await bitrix.call("crm.deal.update", {
            "id": deal_id,
            "fields": {
                "UF_CRM_1740994275251": attached_ids
            }
        })
        logger.debug(f"\U0001F4E4 Bitrix response {update}")
        logger.info(f"✅ Файлы прикреплены: {attached_ids}")
    else:
        logger.warning("\u26a0\ufe0f Нет прикреплённых файлов")

    return {"status": "ok", "attached": attached_ids}