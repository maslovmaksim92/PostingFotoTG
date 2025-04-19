from fastapi import APIRouter, Request
from bitrix_client import get_deal_files

router = APIRouter()


@router.post("/webhook_deal_update")
async def webhook_deal_update(request: Request):
    payload = await request.json()
    deal_id = payload.get("deal_id")
    stage_id = payload.get("stage_id")

    print(f"[Webhook] стадия {stage_id}, сделка {deal_id}")

    if stage_id == "WON":
        deal = await get_deal_files(deal_id)
        print("📎 Данные сделки:", deal)

    return {"status": "received"}