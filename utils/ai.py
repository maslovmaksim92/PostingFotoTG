from openai import AsyncOpenAI
from config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_gpt_text() -> str:
    prompt = (
        "Представь, что ты позитивный бот, восхваляющий труд дворников и уборщиков. "
        "Напиши короткое сообщение после завершения уборки. Можешь использовать стихи, байт на отзыв, вдохновляющие фразы. "
        "Финализируй фразой, призывающей к оценке или отзыву."
    )

    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.9,
    )

    return response.choices[0].message.content.strip()