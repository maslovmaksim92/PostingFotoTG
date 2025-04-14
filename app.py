from fastapi import FastAPI, Request
from pydantic import BaseModel
from utils.bitrix import Bitrix
from utils.folder_db import get_file_ids
import os
from loguru import logger

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
TG_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

app = FastAPI()


class FolderRequest(BaseModel):
    deal_id: int
    folder_id: int


@app.post("/webhook/register_folder")
async def register_folder(data: FolderRequest):
    deal_id = data.deal_id
    folder_id = data.folder_id

    logger.info(f"\U0001F4E5 Вебхук получен: deal={deal_id}, folder={folder_id}")
    
    file_ids = get_file_ids(folder_id)
    logger.info(f"\U0001F4CE Найдено файлов: {file_ids}")

    bitrix = Bitrix()
    attached = []

    for fid in file_ids:
        resp = await bitrix.call("disk.attachedObject.add", {
            "ENTITY_ID": deal_id,
            "ENTITY_TYPE": "crm_deal",
            "OBJECT_ID": fid
        })
        if resp.get("result"):
            attached.append(fid)

    logger.info(f"\U0001F4CE Прикреплено через attachedObject: {attached}")
    return {"status": "ok", "attached": attached}


@app.post("/webhook/test")
async def test_webhook(request: Request):
    data = await request.json()
    return {"status": "ok", "echo": data}