from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/webhook_deal_update")
async def webhook_deal_update(request: Request):
    payload = await request.json()
    print("Webhook получен:", payload)
    return {"status": "received", "payload": payload}