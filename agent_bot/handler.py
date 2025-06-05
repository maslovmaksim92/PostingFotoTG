from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from agent_bot.prompts import get_answer
import os

bot = Bot(token=os.getenv("AGENT_BOT_TOKEN"))
dp = Dispatcher(bot, storage=MemoryStorage())

main_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("📑 Получить КП"),
    KeyboardButton("❓ Задать вопрос"),
    KeyboardButton("📝 Оставить заявку"),
    KeyboardButton("📷 Посмотреть фото"),
)

class Application(StatesGroup):
    waiting_name = State()
    waiting_phone = State()

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот по продаже объекта недвижимости в Калуге.\n\n🏢 *Гостиница 1089 м² + земля 815 м²*\n💰 *Цена*: 45,1 млн ₽\n📍 *Адрес*: Калуга, пер. Сельский, 8а",
        reply_markup=main_kb,
        parse_mode="Markdown"
    )

@dp.message_handler(lambda msg: msg.text == "📑 Получить КП")
async def send_presentation(msg: types.Message):
    await bot.send_message(msg.chat.id, "Вот презентация:")
    await bot.send_document(msg.chat.id, types.InputFile("agent_bot/templates/presentation.pdf"))

@dp.message_handler(lambda msg: msg.text == "📷 Посмотреть фото")
async def send_photos(msg: types.Message):
    files = os.listdir("agent_bot/templates/images")
    media = [types.InputMediaPhoto(open(f"agent_bot/templates/images/{f}", "rb")) for f in files[:10]]
    await bot.send_media_group(msg.chat.id, media)

@dp.message_handler(lambda msg: msg.text == "❓ Задать вопрос")
async def ask_question(msg: types.Message):
    await msg.answer("Напиши свой вопрос:")
    dp.register_message_handler(handle_question, state=None)

async def handle_question(msg: types.Message):
    answer = await get_answer(msg.text)
    await msg.answer(answer)
    dp.unregister_message_handler(handle_question, state=None)

@dp.message_handler(lambda msg: msg.text == "📝 Оставить заявку")
async def start_application(msg: types.Message):
    await msg.answer("Введите своё имя:")
    await Application.waiting_name.set()

@dp.message_handler(state=Application.waiting_name)
async def get_name(msg: types.Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await msg.answer("Теперь номер телефона:")
    await Application.waiting_phone.set()

@dp.message_handler(state=Application.waiting_phone)
async def get_phone(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    phone = msg.text
    await bot.send_message(os.getenv("TG_CHAT_ID"), f"📥 Заявка:\nИмя: {name}\nТелефон: {phone}")
    await msg.answer("Спасибо! Мы свяжемся с вами.")
    await state.finish()

async def start_agent_bot():
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
