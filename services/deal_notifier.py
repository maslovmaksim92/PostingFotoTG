import os
import requests
from senders.telegram import send_telegram_media_group
from utils.prompt_gen import generate_caption

TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")


def fetch_deal(deal_id: str) -> dict:
    url = f"{BITRIX_WEBHOOK}/crm.deal.get.json"
    response = requests.get(url, params={"id": deal_id})
    response.raise_for_status()
    return response.json().get("result", {})


def fetch_deal_files(deal_id: str) -> list[str]:
    url = f"{BITRIX_WEBHOOK}/crm.deal.fields.json"
    return []  # TODO: реализовать при наличии кастомного поля с файлами


def notify_deal_complete(deal_id: str):
    deal = fetch_deal(deal_id)
    caption = generate_caption(deal)
    files = fetch_deal_files(deal_id)  # Пока пустой список

    print(f"📤 Отправка уведомления в Telegram о сделке {deal_id}")
    send_telegram_media_group(chat_id=TG_CHAT_ID, caption=caption, media_urls=files)