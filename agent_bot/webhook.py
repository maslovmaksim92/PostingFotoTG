import os
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from fastapi import APIRouter, Request
from agent_bot.handler import router as main_router
from agent_bot.form import router as form_router

WEBHOOK_PATH = "/webhook/agent"
TOKEN = os.getenv("AGENT_BOT_TOKEN")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(main_router)
dp.include_router(form_router)

api_router = APIRouter()

@api_router.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    update = types.Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}

@dp.startup()
async def on_startup():
    webhook_url = os.getenv("AGENT_WEBHOOK_URL")  # Пример: https://xxx.onrender.com/webhook/agent
    await bot.set_webhook(url=webhook_url, drop_pending_updates=True)
