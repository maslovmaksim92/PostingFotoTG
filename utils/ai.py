from config import settings
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.openai_api_key)


async def generate_message(prompt: str) -> str:
    """
    Генерация ответа от GPT-3.5 на основе предоставленного промпта.
    """
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Ты — помощник, который отвечает кратко и по делу."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content