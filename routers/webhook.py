from fastapi import APIRouter, HTTPException, Request
import os
from bitrix import log_bitrix_payload

router = APIRouter()

CLEANING_DONE_STAGE_ID = "C8:FINISHED"  # Временно, уточняется по логам
APP_TOKEN = os.getenv("BITRIX_TG_WEBHOOK_ISHOD")

@router.post("/webhook/deal_update")
async def webhook_deal_update(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    log_bitrix_payload(payload)

    auth = payload.get("auth", {})
    if auth.get("application_token") != APP_TOKEN:
        raise HTTPException(status_code=403, detail="Неверный токен")

    fields = payload.get("data", {}).get("FIELDS", {})
    current_stage = fields.get("STAGE_ID")
    deal_id = fields.get("ID")

    print(f"[Webhook] Пришёл webhook по сделке {deal_id}, стадия: {current_stage}")

    if current_stage != CLEANING_DONE_STAGE_ID:
        return {"status": "ignored", "reason": "not target stage"}

    print(f"✅ Сделка {deal_id} перешла в стадию 'Уборка завершена'")
    return {"status": "processed", "deal_id": deal_id}