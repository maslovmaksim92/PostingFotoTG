import httpx
import os
from dotenv import load_dotenv

load_dotenv()

TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

async def send_photo(image_url: str, caption: str) -> bool:
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TG_CHAT_ID,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return True
    except Exception as e:
        print("Telegram send error:", e)
        return False