from fastapi import FastAPI
from loguru import logger
from utils.ai import generate_message

app = FastAPI()

@app.get("/")
def health_check():
    logger.info("Health check passed")
    return {"status": "ok"}

# Здесь должны быть остальные маршруты (если есть)
