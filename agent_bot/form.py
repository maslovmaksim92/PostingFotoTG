from aiogram import Router, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram import Bot
import os

router = Router()

bot = Bot(
    token=os.getenv("AGENT_BOT_TOKEN"),
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)

ADMIN_CHAT_ID = -4640675641  # Чат, куда прилетают заявки

class Form(StatesGroup):
    name = State()
    phone = State()
    comment = State()

@router.message(F.text == "📬 Оставить заявку")
async def start_form(msg: Message, state: FSMContext):
    await msg.answer("Как вас зовут?")
    await state.set_state(Form.name)

@router.message(Form.name)
async def form_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await msg.answer("Введите ваш номер телефона")
    await state.set_state(Form.phone)

@router.message(Form.phone)
async def form_phone(msg: Message, state: FSMContext):
    await state.update_data(phone=msg.text)
    await msg.answer("Комментарий или вопрос (необязательно). Если ничего нет — напишите -")
    await state.set_state(Form.comment)

@router.message(Form.comment)
async def form_comment(msg: Message, state: FSMContext):
    await state.update_data(comment=msg.text)
    data = await state.get_data()

    text = (
        f"📬 *Новая заявка от агента*\n"
        f"👤 Имя: {data['name']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"💬 Комментарий: {data['comment']}\n"
        f"🆔 Telegram: [{msg.from_user.full_name}](tg://user?id={msg.from_user.id})"
    )

    await bot.send_message(ADMIN_CHAT_ID, text)
    await msg.answer("✅ Спасибо, заявка отправлена!")
    await state.clear()