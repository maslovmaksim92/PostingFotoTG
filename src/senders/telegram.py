from utils.telegram_client import send_media_group


async def send_telegram_media_group(chat_id: int, media_paths: list[str]):
    await send_media_group(chat_id, media_paths)