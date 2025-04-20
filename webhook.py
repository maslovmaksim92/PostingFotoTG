from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from loguru import logger
from services import send_report
import time
from urllib.parse import parse_qs

router = APIRouter()

last_sent = {}

@router.post("/webhook/register_folder")
async def register_folder(payload: dict):
    deal_id = payload.get("deal_id")
    folder_id = payload.get("folder_id")

    if not deal_id or not folder_id:
        return JSONResponse(content={"error": "Missing deal_id or folder_id"}, status_code=400)

    logger.info(f"📩 Вебхук получен вручную: deal_id={deal_id}, folder_id={folder_id}")
    send_report(deal_id, folder_id)
    return {"status": "ok"}

@router.post("/webhook/deal_update")
async def deal_update(request: Request):
    raw_body = await request.body()
    logger.warning(f"🐞 [deal_update] Сырой payload: {raw_body.decode()} ")

    form = parse_qs(raw_body.decode())
    deal_id = int(form.get("data[FIELDS][ID]", [0])[0])

    now = time.time()
    if deal_id in last_sent and now - last_sent[deal_id] < 30:
        logger.warning(f"⏳ Повторный вызов для {deal_id} — пропускаем")
        return {"status": "skipped"}

    from bitrix import get_deal_fields
    fields = get_deal_fields(deal_id)
    logger.debug(f"📋 Все поля сделки {deal_id}: {fields}")

    folder_id = fields.get("UF_CRM_1743273170850")
    logger.info(f"📬 Из deal_update: deal_id={deal_id}, folder_id={folder_id}")

    last_sent[deal_id] = now
    await send_report(deal_id, folder_id)
    return {"status": "ok"}