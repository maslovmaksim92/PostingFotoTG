import httpx
from loguru import logger
from config import settings

BASE_PROMPT = (
    "Напиши краткое, вдохновляющее сообщение от управляющей компании после завершения уборки. "
    "Сообщение должно быть не длиннее 2-3 предложений. Обязательно:
    - использовать доброжелательный тон
    - похвалить работников
    - завершить позитивной нотой
    - использовать emoji
    Пиши лаконично, но тепло. Не используй хэштеги."
)


async def generate_gpt_text(address: str = "", date: str = "", types: list[str] = None) -> str:
    types = types or []
    context = f"Уборка прошла по адресу {address}. Дата: {date}. Виды уборки: {', '.join(types)}."
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
                    "max_tokens": 150
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"GPT error: {e}")
        raise