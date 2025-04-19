from fastapi import APIRouter, Request
from pydantic import BaseModel
import httpx
from config import settings
from utils.ai import generate_message

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
    message_text = f"Бригада прикрепила фото к сделке #{payload.deal_id}. Папка ID: {payload.folder_id}"

    # Сгенерируем текст через GPT
    try:
        gpt_text = await generate_message(message_text)
    except Exception as e:
        gpt_text = f"[GPT ERROR]: {str(e)}"

    # Отправка в Telegram
    telegram_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(telegram_url, json={
            "chat_id": settings.telegram_chat_id,
            "text": gpt_text
        })

    return {
        "status": "ok",
        "attached": [
            "file1.png",
            "file2.png",
            "example_invoice.pdf"
        ]
    }