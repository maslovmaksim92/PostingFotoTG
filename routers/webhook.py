from fastapi import APIRouter, HTTPException, Request
import os
import json
from urllib.parse import parse_qs
from bitrix import log_bitrix_payload

router = APIRouter()

CLEANING_DONE_STAGE_ID = "C8:FINISHED"
APP_TOKEN = os.getenv("BITRIX_TG_WEBHOOK_ISHOD")

@router.post("/webhook/deal_update")
async def webhook_deal_update(request: Request):
    raw = await request.body()
    body_str = raw.decode("utf-8", errors="ignore")
    form_data = parse_qs(body_str)

    # Расширенное логирование
    log_bitrix_payload({
        "raw": body_str,
        "form_keys": list(form_data.keys()),
        "form_preview": {k: form_data[k][:1] for k in form_data}
    })

    try:
        payload = json.loads(form_data.get("data", [None])[0])
        auth = json.loads(form_data.get("auth", [None])[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Bitrix payload format: {e}")

    if auth.get("application_token") != APP_TOKEN:
        raise HTTPException(status_code=403, detail="Неверный токен")

    fields = payload.get("FIELDS", {})
    current_stage = fields.get("STAGE_ID")
    deal_id = fields.get("ID")

    print(f"[Webhook] Сделка {deal_id}, стадия: {current_stage}")
    if current_stage != CLEANING_DONE_STAGE_ID:
        return {"status": "ignored"}

    print(f"✅ Сделка {deal_id} перешла в 'Уборка завершена'")
    return {"status": "processed", "deal_id": deal_id}