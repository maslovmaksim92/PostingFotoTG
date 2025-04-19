from telegram_sender import send_telegram_media_group

# legacy function for compatibility
async def send_message(chat_id: str, text: str):
    pass  # старый интерфейс, пока оставим

# прокси к новой функции
async def send_telegram_group(chat_id: str, files):
    await send_telegram_media_group(chat_id=chat_id, files=files)