from fastapi import APIRouter, Request
from loguru import logger
from services import send_report

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