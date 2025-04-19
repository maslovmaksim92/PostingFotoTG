from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


@router.get("/ping")
async def ping():
    return {"message": "pong"}


# === Новый маршрут для папки сделки ===
class RegisterFolderPayload(BaseModel):
    deal_id: int
    folder_id: int


@router.post("/webhook/register_folder")
async def register_folder(payload: RegisterFolderPayload):
    # Здесь может быть логика по работе с Bitrix или Telegram
    # Сейчас просто возвращаем то, что получили (заглушка)
    return {
        "status": "ok",
        "attached": [
            "file1.png",
            "file2.png",
            "example_invoice.pdf"
        ]
    }


# Оставляем твой код, если был ниже — ничего не удаляем