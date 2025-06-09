from fastapi import FastAPI
from webhook import router as webhook_router
from loguru import logger
import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from agent_bot.handler import router_polling

# === Проверка токена ===
token = os.getenv("AGENT_BOT_TOKEN")
if not token:
    raise ValueError("❌ AGENT_BOT_TOKEN не найден в .env")

# === Инициализация бота и диспетчера ===
bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# === FastAPI приложение ===
app = FastAPI()
app.include_router(webhook_router)

# === Флаг для защиты от повторного запуска polling ===
polling_started = False

@app.on_event("startup")
async def startup():
    global polling_started
    if not polling_started:
        dp.include_router(router_polling)
        asyncio.create_task(dp.start_polling(bot))
        polling_started = True
        logger.info("✅ FastAPI приложение успешно стартовало с polling запуском")
    else:
        logger.warning("⚠️ Polling уже был запущен — повторный запуск отменён")
