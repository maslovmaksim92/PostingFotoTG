from aiogram import Bot
from aiogram.types import InputMediaPhoto
from pathlib import Path
import os
import asyncio

TELEGRAM_TOKEN = os.getenv("TG_GITHUB_BOT")
CHAT_ID = os.getenv("TG_CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)


async def send_telegram_media_group(chat_id: str | None, files: list[Path]):
    chat_id = chat_id or CHAT_ID
    media = [InputMediaPhoto(media=open(f, "rb")) for f in files]
    await bot.send_media_group(chat_id=chat_id, media=media)


if __name__ == "__main__":
    test_photos = [Path("static/test1.png"), Path("static/test2.png")]
    asyncio.run(send_telegram_media_group(None, test_photos))