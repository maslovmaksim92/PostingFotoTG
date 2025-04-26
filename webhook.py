from fastapi import APIRouter, Request
from loguru import logger
from vas_dom_bitrix24_ru__jit_plugin import getDeal

from bitrix import get_files_from_folder, get_deal_fields, attach_media_to_deal

router = APIRouter()


@router.post("/webhook/deal_update")
async def deal_update(request: Request):
    payload = await request.body()
    logger.warning(f"🐞 [deal_update] Сырой payload: {payload.decode()}")

    data = await request.form()
    deal_id = data.get("data[FIELDS][ID]", "")
    logger.debug(f"📋 Все поля сделки {deal_id}: {await get_deal_fields(deal_id)}")

    folder_id = await get_deal_fields(deal_id).get("UF_CRM_1743273170850", "")
    logger.info(f"📬 Из deal_update: deal_id={deal_id}, folder_id={folder_id}")

    # импорт удалён, вызывется новая логика в другом слое
    # from services import send_report
    # await send_report(deal_id)

    return {"status": "ok"}