import os
from aiogram import Router, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto, FSInputFile
from aiogram.filters import Command
from agent_bot.prompts import get_answer

# === Инициализация роутера ===
router_polling = Router()

# === Кнопки ===
main_kb = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="📑 Получить КП")],
        [KeyboardButton(text="❓ Задать вопрос")],
        [KeyboardButton(text="📷 Фото объекта")],
        [KeyboardButton(text="📩 Оставить заявку")],
    ]
)

# === Обработчики ===

@router_polling.message(Command("start"))
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
    await msg.answer_document(FSInputFile(pdf_path))

@router_polling.message(lambda m: m.text == "📷 Фото объекта")
async def send_photos(msg: Message):
    folder = "agent_bot/templates/images"
    photos = []
    for fname in os.listdir(folder):
        if fname.lower().endswith((".jpg", ".jpeg", ".png")):
            path = os.path.join(folder, fname)
            photos.append(InputMediaPhoto(media=FSInputFile(path)))
    if photos:
        await msg.answer_media_group(photos[:10])
    else:
        await msg.answer("📂 Фото не найдены.")

@router_polling.message(lambda m: m.text == "❓ Задать вопрос")
async def ask_question(msg: Message):
    await msg.answer("🧠 Введите ваш вопрос, я постараюсь ответить.")

@router_polling.message(lambda m: m.text == "📩 Оставить заявку")
async def leave_request(msg: Message):
    chat_id = -4640675641
    user_info = f"👤 {msg.from_user.full_name} (@{msg.from_user.username})\n🆔 {msg.from_user.id}"
    await msg.answer("📬 Ваша заявка отправлена! Мы скоро свяжемся с вами.")
    await msg.bot.send_message(chat_id, f"📥 Новая заявка от пользователя:\n{user_info}")

@router_polling.message()
async def process_question(msg: Message):
    if not msg.text:
        await msg.answer("Пожалуйста, отправьте текстовый вопрос.")
        return
    answer = await get_answer(msg.text)
    await msg.answer(answer)