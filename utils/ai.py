from openai import AsyncOpenAI
from config import settings
from loguru import logger

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_message(prompt: str) -> str:
    logger.info(f"[GPT REQUEST] Prompt: {prompt}")
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content
    logger.info(f"[GPT RESPONSE] Content: {content}")
    return content
