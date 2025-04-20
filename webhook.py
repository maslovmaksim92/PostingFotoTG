from fastapi import APIRouter, Request
from services import process_deal_report
from loguru import logger

router = APIRouter()


@router.post("/webhook/deal_update")
async def deal_update(request: Request):
    try:
        body = await request.body()
        if not body:
            logger.warning("❗ Пустое тело запроса от Bitrix")
            return {"status": "error", "reason": "empty body"}
        payload = await request.json()
    except Exception as e:
        logger.error("❌ Невозможно распарсить JSON: {}", e)
        return {"status": "error", "reason": "invalid JSON"}

    deal = payload.get("deal", {})
    deal_id = deal.get("ID")
    folder_id = deal.get("UF_CRM_1686038818")
    stage_id = deal.get("STAGE_ID")

    if stage_id != "CLEAN_DONE":
        logger.info(f"⏭ Пропущено: стадия {stage_id} ≠ 'CLEAN_DONE'")
        return {"status": "skipped", "reason": "wrong stage"}

    if not deal_id or not folder_id:
        logger.warning("❗ Нет deal_id или folder_id в webhook")
        return {"status": "skip", "reason": "missing data"}

    process_deal_report(int(deal_id), int(folder_id))
    return {"status": "ok"}



@router.post("/webhook/deal_update")
async def deal_update(request: Request):
    try:
        body = await request.body()
        if not body:
            logger.warning("❗ Пустое тело запроса от Bitrix")
            return {"status": "error", "reason": "empty body"}
        payload = await request.json()
    except Exception as e:
        logger.error("❌ Невозможно распарсить JSON: {}", e)
        return {"status": "error", "reason": "invalid JSON"}

    deal = payload.get("deal", {})
    deal_id = deal.get("ID")
    folder_id = deal.get("UF_CRM_1686038818")

    if not deal_id or not folder_id:
        logger.warning("❗ Нет deal_id или folder_id в webhook")
        return {"status": "skip", "reason": "missing data"}

    process_deal_report(int(deal_id), int(folder_id))
    return {"status": "ok"}


@router.get("/")
async def root():
    return {"message": "PostingFotoTG is up and running"}
