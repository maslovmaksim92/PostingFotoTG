from utils.telegram_client import send_media_group

# старый интерфейс
async def send_message(chat_id: str, text: str):
    pass

async def send_telegram_media_group(chat_id: str, files):
    await send_media_group(chat_id, files)