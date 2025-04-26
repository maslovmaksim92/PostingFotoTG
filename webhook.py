from fastapi import APIRouter, Request
from loguru import logger
from bitrix import get_deal_fields, attach_photos_if_cleaning_done
from services import upload_folder_to_deal

router = APIRouter()

last_processed = {}

@router.post("/webhook/deal_update")
async def deal_update(request: Request):
    data = await request.form()
    logger.warning("🐞 [deal_update] Сырой payload: {}", dict(data))

    deal_id = data.get("data[FIELDS][ID]")
    if not deal_id:
        logger.error("❌ Ошибка: нет deal_id в данных запроса")
        return {"status": "error", "message": "No deal_id"}

    # Антиспам (30 секунд)
    import time
    now = time.time()
    if deal_id in last_processed and now - last_processed[deal_id] < 30:
        logger.warning("⏳ Повторный вызов для {} — пропускаем", deal_id)
        return {"status": "skipped", "reason": "too frequent"}

    last_processed[deal_id] = now

    try:
        fields = get_deal_fields(deal_id)
        logger.info("📋 Все поля сделки {}: {}", deal_id, fields)
    except Exception as e:
        logger.error("❌ Ошибка получения полей сделки {}: {}", deal_id, e)
        return {"status": "error", "message": f"Failed to fetch deal fields: {str(e)}"}

    folder_id = fields.get("UF_CRM_1743273170850")
    if not folder_id:
        logger.warning("⚠️ Нет папки у сделки {} (UF_CRM_1743273170850)", deal_id)
        return {"status": "error", "message": "No folder_id in deal"}

    logger.info("📬 Обнаружена папка {} у сделки {}", folder_id, deal_id)

    try:
        # Загружаем файлы из папки в сделку
        upload_folder_to_deal(deal_id=int(deal_id), folder_id=int(folder_id))
        logger.success("✅ Фото из папки {} успешно загружены в сделку {}", folder_id, deal_id)
    except Exception as e:
        logger.error("❌ Ошибка в upload_folder_to_deal для сделки {}: {}", deal_id, e)
        return {"status": "error", "message": str(e)}

    try:
        # Новый шаг: прикрепляем файлы при стадии 'уборка завершена'
        logger.info("🚀 Проверка стадии и прикрепление файлов к сделке {}", deal_id)
        await attach_photos_if_cleaning_done(int(deal_id))
    except Exception as e:
        logger.error("❌ Ошибка в attach_photos_if_cleaning_done для сделки {}: {}", deal_id, e)
        return {"status": "error", "message": f"Failed to attach photos: {str(e)}"}

    return {"status": "ok", "deal_id": deal_id}