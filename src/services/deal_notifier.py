import os
from senders.telegram import send_telegram_media_group

TG_CHAT_ID = int(os.getenv("TG_CHAT_ID"))

async def notify_deal_complete(data: dict):
    stage_id = data.get("stage_id")
    deal_id = data.get("deal_id")

    if stage_id == "WON":  # заменить на реальный ID стадии
        photos = await get_deal_photos(deal_id)
        await send_telegram_media_group(chat_id=TG_CHAT_ID, media_paths=photos)


async def get_deal_photos(deal_id: str) -> list[str]:
    # TODO: заменить на вызов Bitrix
    return ["static/image1.png", "static/image2.png"]