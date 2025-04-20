async def send_message(chat_id: str, text: str):
    print(f"[Mock] Сообщение в чат {chat_id}: {text}")


async def send_telegram_media_group(chat_id, files):
    print("[Mock] Отправка группы медиа в чат:", chat_id)
    for f in files:
        print(" →", f)