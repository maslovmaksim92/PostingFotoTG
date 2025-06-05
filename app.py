from fastapi import FastAPI
from webhook import router as webhook_router
from loguru import logger
from agent_bot.handler import start_agent_bot

@app.on_event("startup")
async def startup():
    asyncio.create_task(start_agent_bot())

# Явно создаём приложение
app = FastAPI()

# Подключаем роутер
app.include_router(webhook_router)

logger.info("✅ FastAPI приложение успешно стартовало")
