from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import os
from bitrix import log_bitrix_payload

router = APIRouter()

class DealUpdatePayload(BaseModel):
    event: str
    data: dict
    auth: dict

CLEANING_DONE_STAGE_ID = "C8:FINISHED"  # Временно, пока не определим точно
APP_TOKEN = os.getenv("BITRIX_TG_WEBHOOK_ISHOD")

@router.post("/webhook/deal_update")
async def webhook_deal_update(payload: DealUpdatePayload, request: Request):
    # Логируем всё, что прилетает
    log_bitrix_payload(payload.dict())

    if payload.auth.get("application_token") != APP_TOKEN:
        raise HTTPException(status_code=403, detail="Неверный токен")

    fields = payload.data.get("FIELDS", {})
    current_stage = fields.get("STAGE_ID")
    deal_id = fields.get("ID")

    if current_stage != CLEANING_DONE_STAGE_ID:
        return {"status": "ignored", "reason": "not target stage"}

    print(f"✅ Сделка {deal_id} перешла в стадию 'Уборка завершена'")
    return {"status": "processed", "deal_id": deal_id}