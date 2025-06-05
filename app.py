from fastapi import FastAPI
from webhook import router as webhook_router
from loguru import logger
from agent_bot.handler import start_agent_bot
import asyncio

# 🟢 Создание FastAPI приложения
app = FastAPI()

# 🟢 Подключение роутера для Bitrix webhook
app.include_router(webhook_router)

# 🟢 Запуск Telegram-бота при старте
@app.on_event("startup")
async def startup():
    asyncio.create_task(start_agent_bot())

logger.info("✅ FastAPI приложение успешно стартовало")
