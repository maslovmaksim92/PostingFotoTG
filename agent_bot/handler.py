import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from agent_bot.prompts import get_answer
from agent_bot.form import Form

# === Бот и диспетчер ===
bot = Bot(
    token=os.getenv("AGENT_BOT_TOKEN"),
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# === Кнопки ===
main_kb = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="📑 Получить КП")],
        [KeyboardButton(text="❓ Задать вопрос")],
        [KeyboardButton(text="📷 Фото объекта")],
        [KeyboardButton(text="✍️ Оставить заявку")],
    ]
)

# === Обработчики ===

@router.message(F.text.lower() == "/start")
async def start_handler(msg: Message):
    await msg.answer(
        "Привет! Я бот по продаже объекта недвижимости в Калуге.\n\n"
        "🏢 *Гостиница 1089 м² + земля 815 м²*\n"
        "💰 *Цена*: 45,1 млн ₽\n"
        "📍 *Адрес*: Калуга, пер. Сельский, 8а\n\n"
        "Выберите действие:",
        reply_markup=main_kb
    )

@router.message(F.text == "📑 Получить КП")
async def send_presentation(msg: Message):
    pdf_path = "agent_bot/templates/Presentation GAB Kaluga.pdf"
    await msg.answer("Вот презентация объекта:")
    await msg.answer_document(FSInputFile(pdf_path))

@router.message(F.text == "📷 Фото объекта")
async def send_photos(msg: Message):
    folder = "agent_bot/images"
    if not os.path.exists(folder):
        await msg.answer("❌ Фото не найдены")
        return

    photos = []
    for fname in os.listdir(folder):
        if fname.endswith((".jpg", ".png", ".jpeg")):
            path = os.path.join(folder, fname)
            photos.append(InputMediaPhoto(media=FSInputFile(path)))
    if photos:
        await msg.answer_media_group(photos[:10])
    else:
        await msg.answer("❌ Фото не найдены")

@router.message(F.text == "❓ Задать вопрос")
async def prompt_question(msg: Message):
    await msg.answer("🧠 Введите ваш вопрос, я постараюсь ответить.")

@router.message(F.text == "✍️ Оставить заявку")
async def ask_name(msg: Message, state: FSMContext):
    await msg.answer("Как вас зовут?")
    await state.set_state(Form.name)

@router.message(Form.name)
async def ask_phone(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await msg.answer("Введите ваш номер телефона:")
    await state.set_state(Form.phone)

@router.message(Form.phone)
async def submit_request(msg: Message, state: FSMContext):
    data = await state.update_data(phone=msg.text)
    name = data["name"]
    phone = data["phone"]
    chat_id = int(os.getenv("LEADS_CHAT_ID", "-4640675641"))

    await bot.send_message(
        chat_id,
        f"📩 Новая заявка!\n👤 Имя: {name}\n📱 Телефон: {phone}"
    )
    await msg.answer("✅ Заявка отправлена. Мы скоро с вами свяжемся.", reply_markup=main_kb)
    await state.clear()

@router.message()
async def process_question(msg: Message):
    if not msg.text:
        await msg.answer("Пожалуйста, отправьте текстовый вопрос.")
        return
    answer = await get_answer(msg.text)
    await msg.answer(answer)

# === Для импорта в FastAPI ===
router_polling = router