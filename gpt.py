import openai
from config import OPENAI_API_KEY
from bitrix import get_address_from_deal
from loguru import logger

openai.api_key = OPENAI_API_KEY


async def generate_caption(deal_id: int) -> str:
    try:
        address = await get_address_from_deal(deal_id)
        prompt = f"""
Вы — бот компании по уборке подъездов. Напишите короткий вдохновляющий текст к фотоотчёту об уборке. 
Адрес: {address}
Упомяните чистоту, благодарность и намёк на социальную ответственность. Добавьте эмодзи.
"""

        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            temperature=0.9,
            messages=[
                {"role": "system", "content": "Ты вдохновляющий помощник по уборке."},
                {"role": "user", "content": prompt}
            ]
        )

        text = response.choices[0].message.content.strip()
        logger.info("🧠 GPT сгенерировал текст")
        return text

    except Exception as e:
        logger.warning(f"⚠️ Ошибка генерации текста: {e}")
        return ""