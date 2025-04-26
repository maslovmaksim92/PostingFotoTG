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
            logger.error("❌ Ошибка: отсутствует deal_id")
            return {"status": "error", "message": "No deal_id"}

        # Антиспам (30 секунд между запросами на одну сделку)
        import time
        now = time.time()
        if deal_id in last_processed and now - last_processed[deal_id] < 30:
            logger.warning("⏳ Повторный вызов для сделки {} — пропускаем", deal_id)
            return {"status": "skipped", "reason": "too frequent"}

        last_processed[deal_id] = now

        # Получаем все поля сделки
        fields = get_deal_fields(deal_id)
        logger.debug("📋 Все поля сделки {}: {}", deal_id, fields)

        stage_id = fields.get("STAGE_ID")
        folder_id = fields.get("UF_CRM_1743273170850")

        if not folder_id:
            logger.error("❗ Ошибка: нет папки у сделки {}", deal_id)
            return {"status": "error", "message": "No folder_id in deal"}

        if stage_id != "CLEAN_DONE":
            logger.info("⏭ Сделка {} не на стадии 'уборка завершена'. Текущая стадия: {}", deal_id, stage_id)
            return {"status": "skipped", "reason": "wrong stage"}

        logger.info("📬 Сделка {} на стадии 'уборка завершена'. Пытаемся загрузить фото.", deal_id)

        try:
            upload_folder_to_deal(deal_id=int(deal_id), folder_id=int(folder_id))
            logger.success("✅ Файлы из папки {} прикреплены к сделке {}", folder_id, deal_id)
            return {"status": "ok", "deal_id": deal_id}
        except Exception as e:
            logger.error("❌ Ошибка в upload_folder_to_deal для сделки {}: {}", deal_id, e)
            return {"status": "error", "message": str(e)}

    except Exception as e:
        logger.exception("❌ Критическая ошибка обработки запроса /deal_update")
        return {"status": "error", "message": str(e)}}