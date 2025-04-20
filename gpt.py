import os
import openai
from loguru import logger

openai.api_key = os.getenv("OPENAI_API_KEY")

FALLBACK_TEXT = "Уборка завершена. Спасибо за чистоту 🧹"


def generate_text(prompt: str = "Напиши вдохновляющий текст об уборке с bait на отзыв") -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0.9,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"**Ошибка GPT**: {e}")
        return FALLBACK_TEXT