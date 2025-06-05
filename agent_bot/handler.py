import os
import asyncio
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from agent_bot.prompts import get_answer
from agent_bot.form import get_contact_form

# === Настройка бота и диспетчера ===
bot = Bot(
    token=os.getenv("AGENT_BOT_TOKEN"),
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()
router_polling = Router()

# === Кнопки ===
main_kb = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="📑 Получить КП")],
        [KeyboardButton(text="❓ Задать вопрос")],
        [KeyboardButton(text="📷 Фото объекта")],
        [KeyboardButton(text="📩 Оставить заявку")]
    ]
)

# === Обработчики ===

@router_polling.message(F.text.lower() == "/start")
async def start_handler(msg: Message):
    await msg.answer(
        "Привет! Я бот по продаже объекта недвижимости в Калуге.\n\n"
        "🏢 *Гостиница 1089 м² + земля 815 м²*\n"
        "💰 *Цена*: 45,1 млн ₽\n"
        "📍 *Адрес*: Калуга, пер. Сельский, 8а\n\n"
        "Выберите действие:",
        reply_markup=main_kb
    )

@router_polling.message(F.text == "📑 Получить КП")
async def send_presentation(msg: Message):
    pdf_path = "agent_bot/templates/Presentation GAB Kaluga.pdf"
    await msg.answer("Вот презентация объекта:")
    await msg.answer_document(types.FSInputFile(pdf_path))

@router_polling.message(F.text == "📷 Фото объекта")
async def send_photos(msg: Message):
    folder = "agent_bot/images"
    photos = []
    if not os.path.exists(folder):
        await msg.answer("❌ Папка с фото не найдена.")
        return
    for fname in os.listdir(folder):
        if fname.endswith((".jpg", ".png", ".jpeg")):
            file_path = os.path.join(folder, fname)
            photos.append(types.InputMediaPhoto(media=types.FSInputFile(file_path)))
    if photos:
        await msg.answer_media_group(photos[:10])
    else:
        await msg.answer("📂 Фото не найдены.")

@router_polling.message(F.text == "❓ Задать вопрос")
async def prompt_question(msg: Message):
    await msg.answer("🧠 Введите ваш вопрос, я постараюсь ответить.")

@router_polling.message(F.text == "📩 Оставить заявку")
async def contact_form(msg: Message):
    await get_contact_form(msg)

@router_polling.message()
async def process_question(msg: Message):
    if not msg.text:
        await msg.answer("❗ Пожалуйста, введите текстовый вопрос.")
        return
    answer = await get_answer(msg.text)
    await msg.answer(answer)

# === Старт бота (используется при webhook запуске) ===
async def start_agent_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

# === Router для подключения в FastAPI ===
dp.include_router(router_polling)