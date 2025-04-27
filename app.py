from fastapi import FastAPI
from webhook import router as webhook_router
from loguru import logger

# Явно создаём приложение
app = FastAPI()

# Подключаем роутер
app.include_router(webhook_router)

logger.info("✅ FastAPI приложение успешно стартовало")