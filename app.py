from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from loguru import logger

from utils.bitrix import fetch_folder_files, download_files, update_deal_files, get_deal_info
from utils.telegram_client import send_photos_batch

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

        info = await get_deal_info(deal_id)
        logger.debug(f"📋 Инфо по сделке: {info}")

        # адрес
        address = info.get("address") or f"ID сделки {deal_id}"
        # даты и типы объединённо
        dates = [d for d in [info.get("date1"), info.get("date2")] if d]
        types = [t for t in [info.get("type1"), info.get("type2")] if t]
        cleaning_date = ", ".join(dates)

        files = await fetch_folder_files(folder_id)
        if not files:
            logger.warning("⚠️ Нет файлов в папке")
            return {"status": "ok", "attached": []}

        file_data = await download_files(files)
        await update_deal_files(deal_id, file_data)

        photo_urls = [f.get("DOWNLOAD_URL") for f in files if f.get("DOWNLOAD_URL") and not f.get("NAME", "").lower().endswith(".mp4")]
        await send_photos_batch(photo_urls, address=address, cleaning_date=cleaning_date, cleaning_types=types)

        return {"status": "ok", "attached": [f['NAME'] for f in files]}

    except Exception as e:
        logger.exception("❌ Ошибка при обработке запроса")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/test")
async def test_webhook(request: Request):
    data = await request.json()
    return {"status": "ok", "echo": data}