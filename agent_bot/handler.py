import os
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from agent_bot.prompts import get_answer
from loguru import logger
from pathlib import Path

bot = Bot(
    token=os.getenv("AGENT_BOT_TOKEN"),
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)

router_polling = Router()

main_kb = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="📑 Получить КП")],
        [KeyboardButton(text="📷 Фото объекта")],
        [KeyboardButton(text="📂 Документы")],
        [KeyboardButton(text="📝 Оставить заявку")],
    ]
)

class Form(StatesGroup):
    waiting_for_contact = State()

@router_polling.message(F.text.lower() == "/start")
async def start_handler(msg: Message):
    logger.info(f"▶️ /start от {msg.from_user.id}")
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

@router_polling.message(F.text == "📷 Фото объекта")
async def send_photos(msg: Message):
    logger.info(f"📷 Пользователь {msg.from_user.id} запросил фото")
    folder = "agent_bot/images"
    if not os.path.exists(folder):
        await msg.answer("❌ Папка с фото не найдена.")
        return

    photos = []
    for fname in sorted(os.listdir(folder)):
        if fname.lower().endswith((".jpg", ".png", ".jpeg")):
            file_path = os.path.join(folder, fname)
            photos.append(InputMediaPhoto(media=FSInputFile(file_path)))

    if not photos:
        await msg.answer("📂 Фото не найдены.")
        return

    for i in range(0, len(photos), 10):
        await msg.answer_media_group(photos[i:i+10])

@router_polling.message(F.text == "📂 Документы")
async def send_documents(msg: Message):
    logger.info(f"📂 Пользователь {msg.from_user.id} запросил документы")
    docs = sorted(Path("agent_bot/templates").glob("*.pdf"))
    if not docs:
        await msg.answer("❌ Документы не найдены.")
        return
    for doc in docs:
        await msg.answer_document(FSInputFile(doc))

@router_polling.message(F.text == "📝 Оставить заявку")
async def start_request_form(msg: Message, state: FSMContext):
    logger.info(f"📝 Пользователь {msg.from_user.id} начал заявку")
    await msg.answer("📞 Введите ваше имя и номер телефона:")
    await state.set_state(Form.waiting_for_contact)

@router_polling.message(Form.waiting_for_contact)
async def process_contact(msg: Message, state: FSMContext):
    user = msg.from_user
    contact_info = (
        f"📥 Новая заявка:\n\n"
        f"👤 Имя и телефон: {msg.text}\n"
        f"🆔 Telegram ID: {user.id}\n"
        f"📨 Username: @{user.username or 'нет'}"
    )

    await bot.send_message(chat_id=os.getenv("TG_CHAT_LEAD"), text=contact_info)
    await msg.answer("✅ Спасибо! Мы свяжемся с вами в ближайшее время.")
    await state.clear()

@router_polling.message(F.text)
async def process_question(msg: Message):
    if not msg.text:
        await msg.answer("⚠️ Пожалуйста, введите текст.")
        return
    logger.info(f"🧠 Вопрос от {msg.from_user.id}: {msg.text}")
    answer = await get_answer(msg.text, msg.from_user.id)
    await msg.answer(answer)
