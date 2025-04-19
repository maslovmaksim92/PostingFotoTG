# Упрощённый импорт только одного метода отправки
from utils.telegram_client import send_media_group


def send_telegram_media_group(chat_id: str, caption: str, media_urls: list[str]):
    if not media_urls:
        # fallback через текст
        send_media_group(chat_id, [{"type": "text", "text": caption}])
        return

    items = [{"type": "photo", "media": url} for url in media_urls]
    items[0]["caption"] = caption
    send_media_group(chat_id, items)