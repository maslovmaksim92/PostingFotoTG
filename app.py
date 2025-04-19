from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from loguru import logger

from utils.bitrix import fetch_folder_files, download_files, update_deal_files
from utils.telegram_client import send_photo_to_telegram

app = FastAPI()


class FolderPayload(BaseModel):
    deal_id: int
    folder_id: int


@app.post("/webhook/register_folder")
async def register_folder(payload: FolderPayload):
    try:
        deal_id = payload.deal_id
        folder_id = payload.folder_id
        logger.info(f"📥 Вебхук получен: deal={deal_id}, folder={folder_id}")

        files = await fetch_folder_files(folder_id)
        if not files:
            logger.warning("⚠️ Нет файлов в папке")
            return {"status": "ok", "attached": []}

        file_data = await download_files(files)
        await update_deal_files(deal_id, file_data)

        if files:
            await send_photo_to_telegram(files[0]["DOWNLOAD_URL"], address=f"ID сделки {deal_id}")

        return {"status": "ok", "attached": [f["NAME"] for f in files]}

    except Exception as e:
        logger.exception("❌ Ошибка при обработке запроса")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/test")
async def test_webhook(request: Request):
    data = await request.json()
    return {"status": "ok", "echo": data}