import os
from openai import AsyncOpenAI
from loguru import logger
from datetime import datetime
import pytz

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Вероятность байта на отзыв (1 из 10)
REVIEW_PROBABILITY = 10
REVIEW_LINKS = (
    "https://yandex.ru/profile/81116139636?lang=ru",
    "https://www.kaluga-poisk.ru/catalog/objects/vash-dom-kaluga",
    "https://2gis.ru/kaluga/search/%D0%92%D0%B0%D1%88%20%D0%B4%D0%BE%D0%BC/firm/70000001064313692/36.250311%2C54.580763",
    "https://zoon.ru/kaluga/building/obsluzhivanie_mnogokvartirnyh_domov_vash_dom_v_moskovskom_rajone/",
)

def get_current_moscow_date() -> str:
    moscow_tz = pytz.timezone("Europe/Moscow")
    now = datetime.now(moscow_tz)
    return now.strftime("%d %B %Y")

async def generate_message(address: str, responsible: str, team: str, include_review: bool = False) -> str:
    prompt = f"""
Ты — позитивный и немного поэтичный Telegram-бот клининговой компании.
Твоя задача — по завершению уборки подъездов сформировать короткое, вдохновляющее сообщение (5-7 строк).
Формат:
1. Заголовок: "Уборка завершена"
2. Адрес (уже вставлен)
3. Ответственный (уже вставлен)
4. Номер бригады (уже вставлен)
5. Мотивационный комментарий: с юмором, в стихах, фразах, цитатах, полезных фактах или продающим контекстом.
Не пиши адрес, дату, ответственного, номер бригады — они будут добавлены отдельно.
Не используй Markdown, только текст.
Всегда разный текст.
"""

    if include_review:
        prompt += """

Также добавь 1-2 предложения с байтом на отзыв, интересным, не однотипным.
Вот ссылки для отзывов (укажи как [ссылка1], [ссылка2]):
""" + "\n".join(REVIEW_LINKS)

    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,
        )
        message = response.choices[0].message.content.strip()
        logger.info(f"🧠 GPT сгенерировал: ---\n{message}")
        return message
    except Exception as e:
        logger.error(f"❌ GPT ошибка: {e}")
        return "Спасибо за чистоту! Команда работает для вашего комфорта. Оцените нас по ссылке: [ссылка1] [ссылка2]"