import httpx
from loguru import logger
from config import settings

BASE_PROMPT = """
Сформулируй креативное, короткое сообщение от лица управляющей компании, завершившей уборку. 
Формат:
- максимум 2–3 строки
- можно в стихах
- можно с шуткой
- обязательно 1 эмоция и 1 результат
- добавь вдохновляющий призыв оставить отзыв (без URL)
- в конце минимум 3 emoji

Пиши живо, тепло, неформально. Без хэштегов. Пример: "В подъезде свежо как весна 🌿 Спасибо нашей команде за чистоту! 💪 Оцените нас добрым словом ✨"
"""


async def generate_gpt_text(address: str = "", date: str = "", types: list[str] = None) -> str:
    types = types or []
    context = f"Уборка по адресу: {address}. Дата: {date}. Типы: {', '.join(types)}."
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": BASE_PROMPT},
                        {"role": "user", "content": context}
                    ],
                    "temperature": 0.9,
                    "max_tokens": 120
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"GPT error: {e}")
        raise