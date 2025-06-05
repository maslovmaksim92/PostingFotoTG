from openai import AsyncOpenAI
import os

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FAQ = {
    "обременения": "Обременений нет. Объект в собственности ООО «Ваш Дом».",
    "аренда": "Мы готовы остаться арендаторами на 3 года по ставке 120 000 ₽/мес.",
}

async def get_answer(question: str) -> str:
    for k, v in FAQ.items():
        if k in question.lower():
            return v
    prompt = f"""
Адрес: Калуга, пер. Сельский, 8а  
Площадь: 1089,7 м² + 815 м² земля  
Цена: 45,1 млн ₽  
Обременения: нет  
Аренда: готовы остаться на 3 года  

Вопрос: {question}
Ответь понятно, уверенно.
"""
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()
