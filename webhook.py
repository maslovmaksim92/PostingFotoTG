from fastapi import APIRouter, Request
from loguru import logger
from services import send_report
from bitrix import get_deal_fields
from urllib.parse import parse_qs

router = APIRouter()

@router.post("/webhook/register_folder")
async def register_folder(request: Request):
    try:
        data = await request.json()
        deal_id = data.get("deal_id")
        folder_id = data.get("folder_id")

        if not deal_id or not folder_id:
            logger.warning(f"❌ Не хватает данных в webhook: {data}")
            return {"status": "error", "message": "Missing deal_id or folder_id"}

        logger.info(f"📬 Вебхук получен: deal_id={deal_id}, folder_id={folder_id}")
        await send_report(deal_id, folder_id)
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"❌ Ошибка обработки webhook: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/webhook/deal_update")
async def deal_update(request: Request):
    try:
        body_bytes = await request.body()
        raw = body_bytes.decode()
        logger.warning(f"🐞 [deal_update] Сырой payload: {raw}")

        form = parse_qs(raw)
        deal_id = int(form.get("data[FIELDS][ID]", [0])[0])
        if not deal_id:
            logger.warning("⚠️ Нет ID сделки в payload")
            return {"status": "no deal id"}

        deal = await get_deal_fields(deal_id)
        logger.debug(f"📋 Все поля сделки {deal_id}: {deal}")

        folder_id = deal.get("UF_CRM_1743273170850")
        if not folder_id:
            logger.warning(f"⚠️ Нет папки в поле UF_CRM_1743273170850 для сделки {deal_id}")
            return {"status": "no folder"}

        logger.info(f"📬 Из deal_update: deal_id={deal_id}, folder_id={folder_id}")
        await send_report(deal_id, folder_id)
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"❌ Ошибка в /deal_update: {e}")
        return {"status": "error", "message": str(e)}