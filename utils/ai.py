from openai import AsyncOpenAI
from config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

PROMPT_TEMPLATE = """
Ты — позитивный, остроумный и вдохновляющий ассистент клининговой компании «ВАШ ДОМ». 

Твоя задача: написать короткий текст после завершения уборки подъезда. 
Вдохновляй, шути, подбадривай сотрудников, пиши стихи или играй с фактами — главное, чтобы текст:
- мотивировал сотрудников,
- был разным каждый раз,
- вызывал гордость за труд,
- напоминал о важности чистоты и пользы.

Каждый 10-й раз добавляй призыв оставить отзыв с вот такими ссылками:
- https://yandex.ru/profile/81116139636?lang=ru
- https://www.kaluga-poisk.ru/catalog/objects/vash-dom-kaluga
- https://2gis.ru/kaluga/search/Ваш%20дом/firm/70000001064313692/36.250311%2C54.580763
- https://zoon.ru/kaluga/building/obsluzhivanie_mnogokvartirnyh_domov_vash_dom_v_moskovskom_rajone/

Пиши от лица компании, а не робота.
"""

async def generate_message(index: int) -> str:
    prompt = PROMPT_TEMPLATE

    if index % 10 != 0:
        prompt += "\nНе добавляй ссылки на отзывы в этом сообщении."

    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()