from telegram_sender import send_telegram_media_group

async def notify_deal_complete(deal_id: str):
    # пока заглушка для фото
    from pathlib import Path
    photo_paths = [Path("static/test1.png"), Path("static/test2.png")]
    await send_telegram_media_group(chat_id=None, files=photo_paths)