import os
import random
from openai import AsyncOpenAI
from loguru import logger

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

REVIEW_LINKS = [
    "https://yandex.ru/profile/81116139636?lang=ru",
    "https://www.kaluga-poisk.ru/catalog/objects/vash-dom-kaluga",
    "https://2gis.ru/kaluga/firm/70000001064313692",
    "https://zoon.ru/kaluga/building/obsluzhivanie_mnogokvartirnyh_domov_vash_dom_v_moskovskom_rajone/",
]

PROMPT_TEMPLATE = """
Ты — телеграм-бот от имени клининговой компании, поздравляющий сотрудников и информирующий клиентов о завершении уборки.
Задача: по каждому сообщению создавать вдохновляющий и креативный текст. В нем должно быть:
- мотивация труда (вдохновляй команду),
- короткий стишок или рифма про чистоту, порядок, пользу,
- лёгкий юмор, но уместно,
- благодарность конкретной бригаде (1 бригада, 2 и т.д.),
- немного философии о труде или важности чистоты.

Если хочешь, примерно раз в 10 сообщений можешь добавить призыв к отзывам — но не всегда.
Если добавляешь — выбери 1–2 ссылки и вставь их внизу:
{review_section}

Формат:
---
🧹 Уборка подъездов завершена  
🏠 Адрес: {address}  
📅 Дата: {date}  
🧑‍🔧 Ответственный: {name}  
🛠 Бригада: {team}  

✉️ Комментарий от бота:
"""


async def generate_message(address: str, date: str, name: str, team: str) -> str:
    review_section = ""
    if random.randint(1, 10) == 1:
        review_section = "\nЕсли вам понравилось — будем рады вашему отзыву:\n" + "\n".join(random.sample(REVIEW_LINKS, 2))

    prompt = PROMPT_TEMPLATE.format(address=address, date=date, name=name, team=team, review_section=review_section)
    logger.debug(f"📨 GPT PROMPT:\n{prompt}")

    try:
        completion = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.1,
            max_tokens=600
        )
        message = completion.choices[0].message.content.strip()
        logger.info(f"🧠 GPT сгенерировал: {message}")
        return message
    except Exception as e:
        logger.error(f"GPT ошибка: {e}")
        return "\u2709️ Комментарий временно недоступен. Но мы ценим ваш труд!"