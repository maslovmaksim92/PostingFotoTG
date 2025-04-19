from fastapi import APIRouter, Request
from telegram_sender import send_telegram_media_group
from pathlib import Path

router = APIRouter()

@router.post("/webhook_deal_update")
async def webhook_deal_update(request: Request):
    payload = await request.json()
    deal_id = payload.get("deal_id")
    stage_id = payload.get("stage_id")

    if stage_id == "WON":
        # Временная заглушка: фото из static/
        photo_paths = [
            Path("static/test1.png"),
            Path("static/test2.png")
        ]
        await send_telegram_media_group(chat_id=None, files=photo_paths)

    return {"status": "ok"}