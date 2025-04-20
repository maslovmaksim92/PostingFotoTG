import aiohttp
import io
from config import TG_CHAT_ID, TG_GITHUB_BOT
from loguru import logger


def build_media_payload(media_group, caption=None):
    payload = []
    for i, item in enumerate(media_group):
        media = {
            "type": "photo",
            "media": f"attach://file{i}"
        }
        if i == 0 and caption:
            media["caption"] = caption
            media["parse_mode"] = "Markdown"
        payload.append(media)
    return payload


async def send_media_group(media_group: list[dict], caption: str):
    url = f"https://api.telegram.org/bot{TG_GITHUB_BOT}/sendMediaGroup"
    data = {
        "chat_id": TG_CHAT_ID,
        "media": build_media_payload(media_group, caption)
    }

    form = aiohttp.FormData()
    form.add_field("chat_id", str(TG_CHAT_ID))
    form.add_field("media", str(data["media"]).replace("'", '"'))

    for i, item in enumerate(media_group):
        form.add_field(
            f"file{i}",
            item["file"],
            filename=item["filename"],
            content_type="image/jpeg"
        )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form) as resp:
                if resp.status == 200:
                    logger.info("📤 Фото успешно отправлены в Telegram")
                else:
                    text = await resp.text()
                    logger.error(f"❌ Ошибка при отправке в Telegram: {resp.status}, {text}")
    except Exception as e:
        logger.error(f"❌ Telegram ошибка: {e}")