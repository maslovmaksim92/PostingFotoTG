import asyncio
import os
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message
from aiogram.enums import ParseMode
from agent_bot.prompts import get_answer

router = Router()
bot = Bot(token=os.getenv("AGENT_BOT_TOKEN"), parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher()

# === Команды ===

@router.message(commands=["start"])
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот по продаже объекта недвижимости в Калуге.\n\n🏢 *Гостиница 1089 м² + земля 815 м²*\n💰 *Цена*: 45,1 млн ₽\n📍 *Адрес*: Калуга, пер. Сельский, 8а\n\nВыберите действие:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="📑 Получить КП")],
                [types.KeyboardButton(text="❓ Задать вопрос")],
                [types.KeyboardButton(text="📷 Фото")],
            ],
            resize_keyboard=True,
        )
    )

@router.message(lambda msg: msg.text == "📑 Получить КП")
async def send_pdf(msg: Message):
    await msg.answer("Вот презентация:")
    await bot.send_document(msg.chat.id, types.FSInputFile("agent_bot/templates/Presentation GAB Kaluga.pdf"))

@router.message(lambda msg: msg.text == "📷 Фото")
async def send_photos(msg: Message):
    folder = "agent_bot/templates/images"
    media = []
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        media.append(types.InputMediaPhoto(types.FSInputFile(path)))
    await bot.send_media_group(msg.chat.id, media[:10])

@router.message(lambda msg: msg.text == "❓ Задать вопрос")
async def ask(msg: Message):
    await msg.answer("Введите ваш вопрос:")

@router.message()
async def fallback(msg: Message):
    response = await get_answer(msg.text)
    await msg.answer(response)


async def start_agent_bot():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
