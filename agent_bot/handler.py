import os
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InputMediaPhoto
from agent_bot.prompts import get_answer
from loguru import logger

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
        [KeyboardButton(text="📩 Оставить заявку")],
        [KeyboardButton(text="🚀 Хочу предложить клиента")],
        [KeyboardButton(text="❓ Задать вопрос")],
    ]
)

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
    logger.info(f"📑 Пользователь {msg.from_user.id} запросил презентацию")
    pdf_path = "agent_bot/templates/Presentation GAB Kaluga.pdf"
    await msg.answer("Вот презентация объекта:")
    await msg.answer_document(FSInputFile(pdf_path))

@router_polling.message(F.text == "📷 Фото объекта")
async def send_photos(msg: Message):
    logger.info(f"📷 Пользователь {msg.from_user.id} запросил фото")
    folder = "agent_bot/images"
    if not os.path.exists(folder):
        await msg.answer("❌ Папка с фото не найдена.")
        return

    photos = []
    for fname in os.listdir(folder):
        if fname.lower().endswith((".jpg", ".png", ".jpeg")):
            file_path = os.path.join(folder, fname)
            photos.append(InputMediaPhoto(media=FSInputFile(file_path)))
    if photos:
        await msg.answer_media_group(photos[:10])
    else:
        await msg.answer("📂 Фото не найдены.")

@router_polling.message(F.text == "📩 Оставить заявку")
async def send_contact_form(msg: Message):
    logger.info(f"📩 Заявка от {msg.from_user.id}")
    full_name = msg.from_user.full_name
    user_id = msg.from_user.id
    text = (
        f"📥 Новая заявка от пользователя:\n\n"
        f"👤 Имя: {full_name}\n"
        f"🆔 Telegram ID: {user_id}\n"
        f"📨 Username: @{msg.from_user.username or 'нет'}\n\n"
        f"📝 Напишите, что вы хотите, и мы свяжемся с вами!"
    )
    await bot.send_message(chat_id=os.getenv("TG_CHAT_ID"), text=text)
    await msg.answer("✅ Заявка отправлена! Мы скоро с вами свяжемся.")

@router_polling.message(F.text == "🚀 Хочу предложить клиента")
async def send_agent_form(msg: Message):
    logger.info(f"🚀 Агент/партнёр {msg.from_user.id} хочет предложить клиента")
    full_name = msg.from_user.full_name
    user_id = msg.from_user.id
    text = (
        f"🚀 Партнёр хочет предложить клиента:\n\n"
        f"👤 Имя: {full_name}\n"
        f"🆔 Telegram ID: {user_id}\n"
        f"📨 Username: @{msg.from_user.username or 'нет'}\n\n"
        f"📣 Проверь, есть ли у тебя прямой клиент. Мы работаем быстро, без воды. "
        f"Если это ты — напиши нам прямо сейчас."
    )
    await bot.send_message(chat_id=os.getenv("TG_CHAT_ID"), text=text)
    await msg.answer("✅ Принято! Мы свяжемся, если клиент интересен.")

@router_polling.message(F.text == "❓ Задать вопрос")
async def ask_question_prompt(msg: Message):
    logger.info(f"❓ Подсказка от бота для вопроса от {msg.from_user.id}")
    await msg.answer("🧠 Введите ваш вопрос — я постараюсь ответить.")

@router_polling.message(F.text)
async def process_question(msg: Message):
    if not msg.text:
        await msg.answer("⚠️ Пожалуйста, введите текст.")
        return
    logger.info(f"🧠 Вопрос от {msg.from_user.id}: {msg.text}")
    answer = await get_answer(msg.text)
    await msg.answer(answer)
