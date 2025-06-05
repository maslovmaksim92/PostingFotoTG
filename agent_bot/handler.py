import os
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InputMediaPhoto
from agent_bot.prompts import get_answer

bot = Bot(
    token=os.getenv("AGENT_BOT_TOKEN"),
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()
router = Router()
dp.include_router(router)

main_kb = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="\ud83d\udcc1 Оставить заявку")],
        [KeyboardButton(text="\ud83d\udcc2 Получить КП")],
        [KeyboardButton(text="\ud83d\udcf7 Фото объекта")],
        [KeyboardButton(text="\u2753 Задать вопрос")],
    ]
)

@router.message(commands=["start"])
async def start_handler(msg: Message):
    await msg.answer(
        "Привет! Я бот по продаже объекта недвижимости в Калуге.\n\n"
        "\ud83c\udfe2 *Гостиница 1089 м\u00b2 + земля 815 м\u00b2*\n"
        "\ud83d\udcb0 *Цена*: 45,1 млн \u20bd\n"
        "\ud83d\udccd *Адрес*: Калуга, пер. Сельский, 8а\n\n"
        "Выберите действие:",
        reply_markup=main_kb
    )

@router.message(lambda m: m.text == "\ud83d\udcc2 Получить КП")
async def send_presentation(msg: Message):
    pdf_path = "agent_bot/templates/Presentation GAB Kaluga.pdf"
    await msg.answer("Вот презентация объекта:")
    await msg.answer_document(FSInputFile(pdf_path))

@router.message(lambda m: m.text == "\ud83d\udcf7 Фото объекта")
async def send_photos(msg: Message):
    folder = "agent_bot/templates/images"
    photos = []
    for fname in os.listdir(folder):
        if fname.endswith((".jpg", ".png", ".jpeg")):
            file_path = os.path.join(folder, fname)
            photo = FSInputFile(file_path)
            photos.append(InputMediaPhoto(media=photo))
    if photos:
        await msg.answer_media_group(photos[:10])
    else:
        await msg.answer("\ud83d\udcc2 Фото не найдены.")

@router.message(lambda m: m.text == "\u2753 Задать вопрос")
async def prompt_question(msg: Message):
    await msg.answer("\ud83e\udde0 Введите ваш вопрос, я постараюсь ответить.")

@router.message()
async def process_question(msg: Message):
    if not msg.text:
        await msg.answer("\u2757 Пожалуйста, отправьте текстовое сообщение.")
        return
    answer = await get_answer(msg.text)
    await msg.answer(answer)
