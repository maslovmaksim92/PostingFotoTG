from fastapi import APIRouter, Request
from loguru import logger
from bitrix import get_deal_fields, attach_photos_if_cleaning_done
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

        folder_id = fields.get("UF_CRM_1743273170850")
        logger.info("📬 Обнаружена папка: deal_id={}, folder_id={}", deal_id, folder_id)

        if not folder_id:
            logger.error("❗ Ошибка: нет папки у сделки {}", deal_id)
            return {"status": "error", "message": "No folder_id in deal"}

        # Загружаем файлы из папки в сделку
        upload_folder_to_deal(deal_id=int(deal_id), folder_id=int(folder_id))
        logger.success("✅ Файлы из папки {} прикреплены к сделке {}", folder_id, deal_id)

        # Дополнительно: если стадия = "уборка завершена", прикрепляем через Bitrix upload
        try:
            logger.info("🚀 Проверяем стадию сделки {} для прикрепления фото", deal_id)
            await attach_photos_if_cleaning_done(int(deal_id))
        except Exception as e:
            logger.error("❌ Ошибка в attach_photos_if_cleaning_done: {}", e)

        return {"status": "ok", "deal_id": deal_id}

    except Exception as e:
        logger.exception("❌ Критическая ошибка обработки запроса /deal_update")
        return {"status": "error", "message": str(e)}}