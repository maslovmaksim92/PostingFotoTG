import os
import random
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    FSInputFile,
    InputMediaPhoto
)
from fastapi import FastAPI, Request
from aiogram.types.update import Update
from agent_bot.prompts import get_answer
from loguru import logger
from pathlib import Path

# === Telegram Bot Setup ===

bot = Bot(
    token=os.getenv("AGENT_BOT_TOKEN"),
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)

router = Router()
dp = Dispatcher()
dp.include_router(router)

# === Webhook FastAPI App ===

app = FastAPI()

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH
TG_CHAT_LEAD = os.getenv("TG_CHAT_LEAD")

# === Клавиатура ===
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="📁 Получить КП")],
            [KeyboardButton(text="📷 Фото объекта")],
            [KeyboardButton(text="📝 Оставить заявку")],
        ]
    )

user_states = {}

@router.message(F.text.lower() == "/start")
async def start_handler(msg: Message):
    logger.info(f"▶️ /start от {msg.from_user.id}")
    await msg.answer(
        "👋 Добро пожаловать! Я — Telegram-ассистент по продаже уникального коммерческого объекта в Калуге.\n\n"
        "🏢 *Объект*: гостиница (1089 м²) с участком (815 м²), переоборудованная под женский исправительный центр — УФИЦ\n"
        "📍 *Адрес*: Калуга, пер. Сельский, 8а\n"
        "💰 *Цена*: 56 млн ₽ *(торг возможен при заинтересованности)*\n"
        "📈 *Доход*: аренда от ООО «Ваш Дом» с передачей объекта в безвозмездное пользование ФСИН (УФИЦ)\n"
        "🗓️ *Срок*: аренда на 10 лет, triple-net (все расходы на арендаторе)\n"
        "🛡️ *Стабильность*: объект работает 24/7, персонал на месте, соответствует СП 308.13330.2012\n"
        "🏛️ *Собственник*: ООО «Ваш Дом»\n\n"
        "🤝 *Мы открыты к сотрудничеству с агентствами недвижимости и инвесторами*.\n"
        "Пишите в любой форме — я отвечу на ваши вопросы, расскажу об условиях и сразу вышлю нужные документы.\n\n"
        "Вы можете:\n"
        "— 📑 Получить КП\n"
        "— 📷 Посмотреть фото\n"
        "— 📝 Оставить заявку\n\n"
        "📩 Или просто задайте вопрос — я всегда на связи!",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "📑 Получить КП")
async def send_presentation(msg: Message):
    logger.info(f"📑 Пользователь {msg.from_user.id} запросил КП")
    docs = sorted(Path("agent_bot/templates").glob("*.pdf"))
    doc_titles = {
        "Presentation GAB Kaluga.pdf": "📊 Коммерческое предложение",
        "egrn.pdf": "📄 Выписка из ЕГРН",
        "resume.pdf": "📋 Резюме объекта",
        "svod_pravil_308.pdf": "📘 Свод правил",
        "tex_plan.pdf": "📐 Технический план",
        "otchet.pdf": "📊 Отчет о рыночной стоимости"
    }
    if not docs:
        await msg.answer("❌ Документы не найдены.")
        return
    await msg.answer("📎 Отправляю все доступные документы по объекту:")
    for doc in docs:
        name = doc.name
        caption = doc_titles.get(name, f"📄 Документ: {name}")
        await msg.answer_document(FSInputFile(doc), caption=caption)

@router.message(F.text == "📷 Фото объекта")
async def send_photos(msg: Message):
    logger.info(f"📷 Пользователь {msg.from_user.id} запросил фото")
    folder = "agent_bot/images"
    if not os.path.exists(folder):
        await msg.answer("❌ Папка с фото не найдена.")
        return
    photos = []
    for fname in sorted(os.listdir(folder)):
        if fname.lower().endswith((".jpg", ".jpeg", ".png")):
            file_path = os.path.join(folder, fname)
            photos.append(InputMediaPhoto(media=FSInputFile(file_path)))
    if not photos:
        await msg.answer("📂 Фото не найдены.")
        return
    for i in range(0, len(photos), 10):
        await msg.answer_media_group(photos[i:i+10])

@router.message(F.text == "📝 Оставить заявку")
async def start_application(msg: Message):
    logger.info(f"📝 Пользователь {msg.from_user.id} начал заявку")
    user_states[msg.from_user.id] = {"step": "name"}
    await msg.answer("✍️ Введите ваше *ФИО*:")

@router.message(F.text)
async def process_form_or_question(msg: Message):
    user_id = msg.from_user.id
    if user_id in user_states:
        state = user_states[user_id]
        if state["step"] == "name":
            state["name"] = msg.text.strip()
            state["step"] = "phone"
            await msg.answer("📞 Введите ваш *номер телефона*:")
            return
        elif state["step"] == "phone":
            state["phone"] = msg.text.strip()
            state["step"] = "done"
            text = (
                f"📥 *Новая заявка!*\n\n"
                f"👤 ФИО: {state['name']}\n"
                f"📞 Телефон: {state['phone']}\n"
                f"🆔 Telegram ID: {user_id}\n"
                f"👤 Username: @{msg.from_user.username or 'нет'}"
            )
            await bot.send_message(chat_id=TG_CHAT_LEAD, text=text)
            await msg.answer("✅ Спасибо! Заявка принята. Мы с вами свяжемся.")
            user_states.pop(user_id, None)
            return
    if not msg.text:
        await msg.answer("⚠️ Пожалуйста, введите текст.")
        return
    logger.info(f"🧠 Вопрос от {msg.from_user.id}: {msg.text}")
    answer = await get_answer(msg.text, user_id=user_id)
    await msg.answer(answer)

@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен: {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    logger.info("🛑 Webhook удалён")
