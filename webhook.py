from fastapi import APIRouter, Request
from loguru import logger
from bitrix import get_deal_fields
from services import send_report

router = APIRouter()

last_processed = {}

@router.post("/webhook/deal_update")
async def deal_update(request: Request):
    data = await request.form()
    logger.warning("🐞 [deal_update] Сырой payload: {}", dict(data))

    deal_id = data.get("data[FIELDS][ID]")
    if not deal_id:
        return {"status": "error", "message": "No deal_id"}

    # Антиспам (30 сек)
    import time
    now = time.time()
    if deal_id in last_processed and now - last_processed[deal_id] < 30:
        logger.warning("⏳ Повторный вызов для {} — пропускаем", deal_id)
        return {"status": "skipped"}

    last_processed[deal_id] = now

    fields = get_deal_fields(deal_id)
    logger.debug("📋 Все поля сделки {}: {}", deal_id, fields)

    folder_id = fields.get("UF_CRM_1743273170850")
    logger.info("📬 Из deal_update: deal_id={}, folder_id={}", deal_id, folder_id)

    if not folder_id:
        return {"status": "error", "message": "No folder_id in deal"}

    try:
        send_report(deal_id=int(deal_id), folder_id=int(folder_id))
        return {"status": "ok"}
    except Exception as e:
        logger.error("❌ Ошибка в send_report для сделки {}: {}", deal_id, e)
        return {"status": "error", "message": str(e)}