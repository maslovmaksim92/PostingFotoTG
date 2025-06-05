from openai import AsyncOpenAI
import os

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FAQ = {
    "обременения": "Обременений нет. Объект в собственности ООО «Ваш Дом».",
    "аренда": "Мы готовы остаться арендаторами на 3 года по ставке 120 000 ₽/мес.",
    "площадь": "Площадь здания — 1089,7 м², участок — 815 м².",
    "адрес": "г. Калуга, пер. Сельский, д. 8а.",
    "цена": "Стоимость объекта — 45,1 млн ₽.",
}

async def get_answer(question: str) -> str:
    for key, value in FAQ.items():
        if key in question.lower():
            return value

    prompt = f"""
Вот данные по объекту:

📍 Адрес: Калуга, пер. Сельский, 8а  
🏢 Площадь: 1089,7 м²  
🪧 Земля: 815 м²  
💰 Цена: 45,1 млн ₽  
📄 Обременения: нет  
📃 ДДУ: отсутствует  
📎 Мы готовы остаться арендаторами на 3 года (120 тыс./мес)

Вопрос агента: "{question}"
Ответь как агент по недвижимости.
"""

    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return response.choices[0].message.content.strip()
