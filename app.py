from fastapi import FastAPI

from utils.tg import router as telegram_router

app = FastAPI()

app.include_router(telegram_router)