from utils.telegram_client import send_message, send_photo, send_media_group

__all__ = ["send_telegram_media_group"]

def send_telegram_media_group(chat_id: str, caption: str, media_urls: list[str]):
    if not media_urls:
        send_message(chat_id, caption)
        return

    # Fallback — просто первая фотка + текст
    send_photo(chat_id, media_urls[0], caption=caption)