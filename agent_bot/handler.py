from aiogram import Router, F, types
from aiogram.types import Message, FSInputFile, InputMediaPhoto, KeyboardButton, ReplyKeyboardMarkup
from pathlib import Path

router = Router()

@router.message(F.text == "📂 Документы")
async def send_all_documents(message: Message):
    docs = sorted(Path("agent_bot/templates").glob("*.pdf"))
    if not docs:
        await message.answer("Документы не найдены.")
        return

    for path in docs:
        await message.answer_document(FSInputFile(path))