import os
import asyncio
from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from agent_bot.prompts import get_answer

# === Отдельный router для polling ===
router_polling = Router()

# === Кнопки ===
main_kb = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="📑 Получить КП")],
        [KeyboardButton(text="❓ Задать вопрос")],
        [KeyboardButton(text="📷 Фото объекта")],
    ]
)

# === Обработчики ===

@router_polling.message(commands=["start"])
async def start_handler(msg: Message):
    await msg.answer(
        "Привет! Я бот по продаже объекта недвижимости в Калуге.\n\n"
        "🏢 *Гостиница 1089 м² + земля 815 м²*\n"
        "💰 *Цена*: 45,1 млн ₽\n"
        "📍 *Адрес*: Калуга, пер. Сельский, 8а\n\n"
        "Выберите действие:",
        reply_markup=main_kb
    )

@router_polling.message(lambda m: m.text == "📑 Получить КП")
async def send_presentation(msg: Message):
    pdf_path = "agent_bot/templates/Presentation GAB Kaluga.pdf"
    await msg.answer("Вот презентация объекта:")
    await msg.answer_document(types.FSInputFile(pdf_path))

@router_polling.message(lambda m: m.text == "📷 Фото объекта")
async def send_photos(msg: Message):
    folder = "agent_bot/templates/images"
    photos = []
    for fname in os.listdir(folder):
        if fname.endswith((".jpg", ".png", ".jpeg")):
            file_path = os.path.join(folder, fname)
            photos.append(types.InputMediaPhoto(types.FSInputFile(file_path)))
    if photos:
        await msg.answer_media_group(photos[:10])
    else:
        await msg.answer("📂 Фото не найдены.")

@router_polling.message(lambda m: m.text == "❓ Задать вопрос")
async def prompt_question(msg: Message):
    await msg.answer("🧠 Введите ваш вопрос, я постараюсь ответить.")

@router_polling.message()
async def process_question(msg: Message):
    answer = await get_answer(msg.text)
    await msg.answer(answer)
