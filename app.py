from fastapi import FastAPI
from webhook import router as webhook_router
from loguru import logger
import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from agent_bot.handler import router_polling

# === Инициализация бота и диспетчера ===
bot = Bot(token=os.getenv("AGENT_BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()
dp.include_router(router_polling)

# === FastAPI приложение ===
app = FastAPI()
app.include_router(webhook_router)

# === Запуск polling при старте ===
@app.on_event("startup")
async def startup():
    asyncio.create_task(dp.start_polling(bot))
    logger.info("✅ FastAPI приложение успешно стартовало")