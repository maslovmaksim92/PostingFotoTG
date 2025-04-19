import httpx
from loguru import logger
from config import settings

BASE_PROMPT = (
    "Сформулируй одно вдохновляющее предложение от лица управляющей компании после завершения уборки."
    " Обязательно:
    - доброе настроение
    - краткость
    - не более 1 предложения
    - emoji
    Без хэштегов. Без воды."
)


async def generate_gpt_text(address: str = "", date: str = "", types: list[str] = None) -> str:
    types = types or []
    context = f"Уборка по адресу {address}. Дата: {date}. Виды: {', '.join(types)}."
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
                    "temperature": 0.85,
                    "max_tokens": 70
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"GPT error: {e}")
        raise