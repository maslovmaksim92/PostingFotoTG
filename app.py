from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from loguru import logger
from utils.bitrix import Bitrix
from utils.folder_db import get_file_ids
import os

app = FastAPI()


class FolderRequest(BaseModel):
    deal_id: int
    folder_id: int


@app.post("/webhook/register_folder")
async def register_folder(data: FolderRequest):
    try:
        deal_id = data.deal_id
        folder_id = data.folder_id

        logger.info(f"\U0001F4E5 Вебхук получен: deal={deal_id}, folder={folder_id}")

        file_ids = get_file_ids(folder_id)
        logger.info(f"\U0001F4CE Найдено файлов: {file_ids}")

        bitrix = Bitrix()
        attached = []

        for fid in file_ids:
            try:
                resp = await bitrix.call("disk.attachedObject.add", {
                    "ENTITY_ID": deal_id,
                    "ENTITY_TYPE": "crm_deal",
                    "OBJECT_ID": fid
                })
                if resp.get("result"):
                    attached.append(fid)
            except Exception as e:
                logger.error(f"❌ Ошибка при добавлении файла {fid}: {e}")

        logger.info(f"\U0001F4CC Прикреплено к сделке: {attached}")
        return {"status": "ok", "attached": attached}

    except Exception as e:
        logger.exception("❌ Ошибка при выполнении register_folder")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/test")
async def test_webhook(request: Request):
    data = await request.json()
    return {"status": "ok", "echo": data}