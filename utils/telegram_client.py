import os
import httpx
from loguru import logger
from utils.ai import generate_gpt_text

TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

SEND_PHOTO_API = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
SEND_MEDIA_GROUP_API = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMediaGroup"
SEND_VIDEO_API = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendVideo"


def build_fallback_text(address: str) -> str:
    return (
        f"\U0001F9F9 Уборка завершена\n"
        f"\U0001F3E0 Адрес: {address}\n"
        f"📣 Благодарим за ваш труд и заботу о доме!"
    )


async def send_photo_to_telegram(image_url: str, address: str, cleaning_date: str = "", cleaning_types: list[str] = None):
    if cleaning_types is None:
        cleaning_types = []
    try:
        gpt_text = await generate_gpt_text(address, cleaning_date, cleaning_types)
    except Exception as e:
        logger.warning(f"⚠️ GPT недоступен: {e}, используем fallback-текст")
        gpt_text = build_fallback_text(address)

    text = (
        f"\U0001F9F9 Уборка подъездов завершена\n"
        f"\U0001F3E0 Адрес: {address}\n\n"
        f"{gpt_text}"
    )
    logger.info(f"\U0001F4F7 Отправка 1 фото в Telegram: {image_url}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            SEND_PHOTO_API,
            data={"chat_id": TG_CHAT_ID, "caption": text, "photo": image_url, "parse_mode": "HTML"},
        )

    if response.status_code != 200:
        logger.warning(f"❌ Telegram error: {response.text}")
    else:
        logger.info("✅ Фото отправлено в Telegram")


async def send_photos_batch(photo_urls: list[str], address: str = "", cleaning_date: str = "", cleaning_types: list[str] = None):
    if cleaning_types is None:
        cleaning_types = []
    if not photo_urls:
        return

    try:
        gpt_text = await generate_gpt_text(address, cleaning_date, cleaning_types)
    except Exception as e:
        logger.warning(f"⚠️ GPT недоступен: {e}, используем fallback-текст")
        gpt_text = build_fallback_text(address)

    caption = (
        f"\U0001F9F9 Уборка подъездов завершена\n"
        f"\U0001F3E0 Адрес: {address}\n\n"
        f"{gpt_text}"
    )

    logger.info(f"📦 Отправка {len(photo_urls)} фото партиями")
    async with httpx.AsyncClient() as client:
        for i in range(0, len(photo_urls), 10):
            batch = photo_urls[i:i + 10]
            media = [
                {"type": "photo", "media": url, **({"caption": caption, "parse_mode": "HTML"} if j == 0 else {})}
                for j, url in enumerate(batch)
            ]
            resp = await client.post(SEND_MEDIA_GROUP_API, json={"chat_id": TG_CHAT_ID, "media": media})
            if resp.status_code != 200:
                logger.warning(f"❌ Ошибка Telegram: {resp.text}")
            else:
                logger.info(f"✅ Пакет {i // 10 + 1} отправлен")


async def send_video_to_telegram(video_url: str, caption: str = "") -> None:
    logger.info(f"🎥 Отправка видео в Telegram: {video_url}")
    async with httpx.AsyncClient() as client:
        resp = await client.post(SEND_VIDEO_API, data={
            "chat_id": TG_CHAT_ID,
            "video": video_url,
            "caption": caption,
            "parse_mode": "HTML"
        })
        if resp.status_code != 200:
            logger.warning(f"❌ Ошибка Telegram (видео): {resp.text}")
        else:
            logger.info("✅ Видео отправлено")