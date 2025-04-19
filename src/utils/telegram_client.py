import os
from aiogram import Bot
from aiogram.types import InputMediaPhoto

bot = Bot(token=os.getenv("TG_GITHUB_BOT"))

async def send_media_group(chat_id: int, media_paths: list[str]):
    media = [InputMediaPhoto(media=open(path, "rb")) for path in media_paths]
    await bot.send_media_group(chat_id=chat_id, media=media)
