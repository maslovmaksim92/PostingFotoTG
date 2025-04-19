# 🔧 Заглушка — временно отключена отправка в Telegram

async def send_telegram_media_group(chat_id, files):
    print("[Mock] Отправка в Telegram отключена. Chat:", chat_id, "Files:", files)

async def send_message(chat_id: str, text: str):
    print("[Mock] Сообщение в Telegram:", text)