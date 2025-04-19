from openai import AsyncOpenAI
from config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_gpt_text(address: str, cleaning_date: str, cleaning_types: list[str]) -> str:
    cleaning_types_text = ", ".join(cleaning_types)
    prompt = (
        f"Представь, что ты доброжелательный Telegram-бот управляющей компании. "
        f"Опиши завершённую уборку по адресу: {address}. Укажи график: {cleaning_date} и виды: {cleaning_types_text}. "
        f"Используй лёгкий стиль, вдохнови похвалой работников и закончи хэштегами: #уборкаподъездов #Калуга #ВашДом."
    )

    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=250,
        temperature=0.95,
    )

    return response.choices[0].message.content.strip()