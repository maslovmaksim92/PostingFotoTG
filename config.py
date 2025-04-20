import os
from dotenv import load_dotenv

load_dotenv()

TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_GITHUB_BOT = os.getenv("TG_GITHUB_BOT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")