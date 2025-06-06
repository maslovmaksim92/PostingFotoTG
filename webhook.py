import time
from fastapi import APIRouter, Request
from loguru import logger
from bitrix import get_deal_fields
from services import upload_folder_to_deal

router = APIRouter()
last_processed = {}

@router.post("/webhook/deal_update")
async def deal_update(request: Request):
    try:
        data = await request.form()
        logger.warning("🐞 [deal_update] Сырой payload: {}", dict(data))

        deal_id = data.get("data[FIELDS][ID]")
        if not deal_id:
            logger.error("❌ Ошибка: отсутствует deal_id в данных запроса")
            return {"status": "error", "message": "Deal ID not provided"}

        now = time.time()
        if deal_id in last_processed and now - last_processed[deal_id] < 30:
            logger.warning("⏳ Повторный вызов для сделки {} — пропускаем", deal_id)
            return {"status": "skipped", "reason": "duplicate request"}

        last_processed[deal_id] = now

        fields = await get_deal_fields(int(deal_id))
        logger.debug("📋 Все поля сделки {}: {}", deal_id, fields)

        folder_id = fields.get("UF_CRM_1743273170850")
        logger.info("📬 Из deal_update: deal_id={}, folder_id={}", deal_id, folder_id)

        if not folder_id:
            logger.error("❗ Нет папки у сделки {}", deal_id)
            return {"status": "error", "message": "Folder ID not found in deal"}

        await upload_folder_to_deal(deal_id=int(deal_id), folder_id=int(folder_id))
        logger.success("✅ Файлы успешно прикреплены к сделке {}", deal_id)
        return {"status": "ok", "deal_id": deal_id}

    except Exception as e:
        logger.exception("❌ Критическая ошибка обработки сделки")
        return {"status": "error", "message": f"Internal server error: {str(e)}"}
