import os
from openai import AsyncOpenAI
from loguru import logger

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

PROMPT_TEMPLATE = """
Ты — телеграм-бот от имени клининговой компании, поздравляющий сотрудников и информирующий клиентов о завершении уборки.
Задача: по каждому сообщению создавать вдохновляющий и креативный текст. В нем должно быть:
- мотивация труда (вдохновляй команду),
- короткий стишок или рифма про чистоту, порядок, пользу,
- лёгкий юмор, но уместно,
- благодарность конкретной бригаде (1 бригада, 2 и т.д.),
- немного философии о труде или важности чистоты.

⚠️ В конце обязательно добавь призыв оставить отзыв с добрым посылом, желательно с юмором и намёком на совесть (если не оставишь — совесть может съесть).

Обязательно вставь одну из ссылок на отзывы (можно поочерёдно менять или упоминать 2–3):
- https://yandex.ru/profile/81116139636?lang=ru
- https://www.kaluga-poisk.ru/catalog/objects/vash-dom-kaluga
- https://2gis.ru/kaluga/search/%D0%92%D0%B0%D1%88%20%D0%B4%D0%BE%D0%BC/firm/70000001064313692/36.250311%2C54.580763
- https://zoon.ru/kaluga/building/obsluzhivanie_mnogokvartirnyh_domov_vash_dom_v_moskovskom_rajone/

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
    prompt = PROMPT_TEMPLATE.format(address=address, date=date, name=name, team=team)
    try:
        completion = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.1,
            max_tokens=600
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"GPT ошибка: {e}")
        return "\u2709️ Комментарий временно недоступен. Но мы ценим ваш труд! И ждём добрых слов о нас на сайтах с отзывами :)"