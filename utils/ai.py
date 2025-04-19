from openai import OpenAI
from core.config import settings

def generate_gpt_text(deal: dict) -> str:
    # Пример генерации описания на основе сделки
    title = deal.get("TITLE", "Без названия")
    return f"Описание по сделке: {title} — будет сгенерировано GPT"