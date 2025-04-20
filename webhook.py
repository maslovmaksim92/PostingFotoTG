from fastapi import APIRouter, Request
from services import process_deal_report
from loguru import logger

router = APIRouter()


@router.post("/webhook/register_folder")
async def register_folder(payload: dict):
    deal_id = payload.get("deal_id")
    folder_id = payload.get("folder_id")
    if not deal_id or not folder_id:
        return {"status": "error", "message": "Missing deal_id or folder_id"}

    process_deal_report(deal_id, folder_id)
    return {"status": "ok"}


@router.post("/webhook/deal_update")
async def deal_update(payload: dict):
    deal = payload.get("deal", {})
    deal_id = deal.get("ID")
    folder_id = deal.get("UF_CRM_1686038818")

    if not deal_id or not folder_id:
        logger.warning("Нет deal_id или folder_id в webhook")
        return {"status": "skip", "reason": "missing data"}

    process_deal_report(int(deal_id), int(folder_id))
    return {"status": "ok"}


@router.get("/")
async def root():
    return {"message": "PostingFotoTG is up and running"}