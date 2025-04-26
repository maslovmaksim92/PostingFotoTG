import loguru

def send_media_group(photos, address):
    from gpt import generate_caption, fallback_caption

    if not address:
        loguru.logger.warning("Адрес объекта не указан, используем fallback")

    loguru.logger.info(f"Адрес объекта для подписи: {address}")

    caption = generate_caption(address=address) or fallback_caption()
    # Далее отправка в Telegram
    return True  # заглушка