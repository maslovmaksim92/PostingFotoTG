from openai import AsyncOpenAI
from config import settings
from loguru import logger

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

PROMPT_TEMPLATE = (
    "Представь, что ты позитивный бот, восхваляющий труд дворников и уборщиков. "
    "Напиши короткое сообщение после завершения уборки. "
    "Добавь немного эмоций, можешь использовать стихи, байт на отзыв, вдохновляющие фразы. "
    "Финализируй фразой, призывающей к оценке или отзыву."
)


async def generate_message(_: str = "") -> str:
    logger.info("[GPT REQUEST] Prompt: %s", PROMPT_TEMPLATE)
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": PROMPT_TEMPLATE},
        ],
    )
    content = response.choices[0].message.content
    logger.info("[GPT RESPONSE] Content: %s", content)
    return content
