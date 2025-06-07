import os
import random
from datetime import datetime
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FAQ = {
    "обременени": "🔐 На объекте есть обременение (ипотека), которое будет полностью погашено до выхода на сделку.",
    "аренд": "🏢 Арендатор — ООО «Ваш Дом». Объект передан УФИЦ (ФСИН) в безвозмездное пользование, что гарантирует устойчивую загрузку.",
    "фсин": (
        "👥 Объект используется УФИЦ — участком, функционирующим как исправительный центр под юрисдикцией ФСИН. "
        "Здание оборудовано по *СП 308.13330.2012*, работает круглосуточно (режим 24/7), персонал на месте. "
        "Установлены системы видеонаблюдения. Порядок и безопасность обеспечены."
    ),
    "уфиц": "🔒 УФИЦ — это формат исправительного центра. Персонал круглосуточно. Полное соответствие СП 308.",
    "женский": "👥 Это женский исправительный центр. Работа 24/7. Постоянное присутствие персонала.",
    "сп 308": "📘 По СП 308.13330.2012 здание соответствует требованиям ФСИН. Готов выслать PDF-файл по запросу.",
    "оценка": "📊 У нас есть независимая оценка стоимости. При интересе отправим документ."
}

BAD_PATTERNS = ["просто смотрю", "не знаю", "пока нет", "интересуюсь"]

FILE_MENTION = {
    "сп 308": "📘 Можем отправить файл СП 308.13330.2012 по запросу.",
    "оценка": "📊 У нас есть PDF с независимой оценкой — вышлем при интересе.",
    "техплан": "📐 Техплан доступен, отправим по запросу."
}

SUMMARY = """
📍 *Адрес*: Калуга, пер. Сельский, 8а  
🏢 *Объект*: гостиница, переоборудованная под УФИЦ (исправительный центр)  
📐 *Площадь*: 1089,7 м² + 815 м² (земля)  
💰 *Цена*: 56 млн ₽ (возможен торг)  
👮 *ФСИН / УФИЦ*: аренда на 10 лет, круглосуточный режим, штат сотрудников  
📋 *Документы*: техплан, ЕГРН, презентация, оценка, свод правил  
🔒 *Обременение*: будет снято до сделки  
🏛️ *Собственник*: ООО «Ваш Дом»
"""

STYLE_PROMPT = """
Ты — дружелюбный Telegram-ассистент по продаже недвижимости.  
Твоя задача — не просто ответить, а помочь, вовлечь в диалог и убедить в выгоде.  
Отвечай уверенно, но живо. Заверши каждый ответ уточняющим вопросом.  
Если клиент подходит — предложи документы. Если нет — фильтруй вежливо.
"""

# 🧩 Персонализация CTA и follow-up
AGENT_CUES = ["я агент", "у меня клиент", "работаю с инвестором", "брокер"]
INVESTOR_CUES = ["ищу для себя", "хочу вложить", "смотрю для покупки"]

CTA_AGENT = [
    "📎 Пришлю техплан, ЕГРН и презентацию — только напишите",
    "📥 Готов отправить документы — если у вас есть клиент",
    "🗂 Есть КП, оценка и презентация — пишите, всё вышлю"
]

CTA_INVESTOR = [
    "📩 Отправим КП и документы — напишите сюда",
    "📊 Хочу выслать вам оценку и презентацию",
    "📥 Могу предложить материалы — стоит ли отправить?"
]

FOLLOWUP_AGENT = [
    "🧾 Уточните, интересен ли объект для вашего клиента?",
    "📞 С кем из вашей команды можно обсудить условия сделки?",
    "📬 Готов передать документы — ваш клиент на связи?"
]

FOLLOWUP_INVESTOR = [
    "💬 Готовы перейти к просмотру документов?",
    "📊 Рассматриваете покупку в ближайшие недели?",
    "📎 Хотите сразу посмотреть оценку и техплан?"
]

def detect_persona(text: str) -> str:
    text = text.lower()
    if any(cue in text for cue in AGENT_CUES):
        return "agent"
    if any(cue in text for cue in INVESTOR_CUES):
        return "investor"
    return "neutral"

async def get_answer(question: str, user_id: int = None) -> str:
    q_lower = question.lower()

    for keyword, reply in FAQ.items():
        if keyword in q_lower:
            return reply

    if any(p in q_lower for p in BAD_PATTERNS):
        return "🧐 Уточните, вы представляете клиента или просто изучаете рынок?"

    persona = detect_persona(q_lower)

    if persona == "agent":
        cta = random.choice(CTA_AGENT)
        followup = random.choice(FOLLOWUP_AGENT)
    elif persona == "investor":
        cta = random.choice(CTA_INVESTOR)
        followup = random.choice(FOLLOWUP_INVESTOR)
    else:
        cta = random.choice(CTA_AGENT + CTA_INVESTOR)
        followup = random.choice(FOLLOWUP_AGENT + FOLLOWUP_INVESTOR)

    file_hint = ""
    for keyword, hint in FILE_MENTION.items():
        if keyword in q_lower:
            file_hint = f"\n📎 {hint}"
            break

    prompt = f"""{SUMMARY}

{STYLE_PROMPT}

Вопрос клиента: "{question}"

Ответ:  
1. ✳️ Суть предложения  
2. 💼 Преимущество объекта (ФСИН, аренда на 10 лет, готовность документов)  
3. 📎 {cta}{file_hint}  
4. ❓ {followup}
"""

    try:
        if user_id:
            with open("logs/questions.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] {user_id}: {question}\n")
    except Exception:
        pass

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "📍 Объект функционирует. Документы готовы. Уточните, вы представляете клиента?"
