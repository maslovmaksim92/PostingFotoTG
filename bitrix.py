import httpx
from loguru import logger
from config import BITRIX_WEBHOOK

...

async def add_comment_to_deal(deal_id: int, text: str) -> None:
    url = f"{BITRIX_WEBHOOK}/crm.timeline.comment.add"
    payload = {
        "fields": {
            "ENTITY_ID": deal_id,
            "ENTITY_TYPE": "deal",
            "COMMENT": text
        }
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logger.info(f"💬 Комментарий добавлен в сделку {deal_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении комментария в сделку {deal_id}: {e}")