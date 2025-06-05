from fastapi import FastAPI, Request
from webhook import router as webhook_router
from loguru import logger
from agent_bot.handler import start_agent_bot
from agent_bot.webhook import api_router as tg_webhook_router, on_startup as tg_webhook_startup
import asyncio

# 🟢 Создание FastAPI приложения
app = FastAPI()

# 🟢 Подключение роутеров
app.include_router(webhook_router)        # Bitrix webhook
app.include_router(tg_webhook_router)     # Telegram webhook

# 🟢 Старт при запуске
@app.on_event("startup")
async def startup():
    # ✅ Старт Telegram webhook
    await tg_webhook_startup()

    # ⛔ Если хочешь использовать polling (например, в dev-среде) — раскомментируй:
    # asyncio.create_task(start_agent_bot())

logger.info("✅ FastAPI приложение успешно стартовало")
