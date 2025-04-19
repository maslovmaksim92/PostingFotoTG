from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
async def ping():
    return {"message": "pong"}

# Оставляем твой код, если был ниже — ничего не удаляем

# ... (здесь может быть твоя логика отправки в Telegram и т.п.)