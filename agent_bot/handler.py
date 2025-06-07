import os
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InputMediaPhoto
from agent_bot.prompts import get_answer
from loguru import logger
from pathlib import Path

bot = Bot(token=os.getenv("AGENT_BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
router_polling = Router()

main_kb = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="📑 Получить КП")],
        [KeyboardButton(text="📷 Фото объекта")],
        [KeyboardButton(text="📩 Оставить заявку")],
        [KeyboardButton(text="🚀 Хочу предложить клиента")],
        [KeyboardButton(text="❓ Задать вопрос")],
    ]
)

@router_polling.message(F.text == "📑 Получить КП")
async def send_all_documents(msg: Message):
    logger.info(f"📑 Пользователь {msg.from_user.id} запросил КП")
    docs = sorted(Path("agent_bot/templates").glob("*.pdf"))

    doc_titles = {
        "Presentation GAB Kaluga.pdf": "📊 Коммерческое предложение",
        "egrn.pdf": "📄 Выписка из ЕГРН",
        "resume.pdf": "📋 Резюме объекта",
        "svod_pravil_308.pdf": "📘 Свод правил",
        "tex_plan.pdf": "📐 Технический план"
    }

    if not docs:
        await msg.answer("❌ Документы не найдены.")
        return

    await msg.answer("📎 Отправляю все документы по объекту:")

    for doc in docs:
        name = doc.name
        caption = doc_titles.get(name, f"📄 Документ: {name}")
        await msg.answer_document(FSInputFile(doc), caption=caption)

# остальные хендлеры остаются без изменений...