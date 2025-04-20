# ... (импорт и другие функции остаются без изменений)

async def attach_media_to_deal(deal_id: int, media_group: list[dict], folder_id: int) -> None:
    bind_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
    field_code = "UF_CRM_1740994275251"

    file_ids = [f["id"] for f in media_group if f.get("id")]

    if not file_ids:
        logger.warning(f"⚠️ Нет ID файлов для прикрепления (media_group пустой или без ID)")
        return

    try:
        bind_payload = {
            "id": deal_id,
            "fields": {
                field_code: file_ids
            }
        }
        logger.debug(f"➡️ CRM PAYLOAD (getchildren): {bind_payload}")
        async with httpx.AsyncClient() as client:
            update_resp = await client.post(bind_url, json=bind_payload)
            update_resp.raise_for_status()
            result = update_resp.json()
            logger.debug(f"📨 Ответ от Bitrix: {result}")
            if result.get("result") is True:
                logger.info(f"📎 Файлы прикреплены к сделке {deal_id}: {file_ids}")
            else:
                logger.warning(f"⚠️ Bitrix не подтвердил обновление сделки {deal_id}: {result}")
    except Exception as e:
        logger.error(f"❌ Ошибка привязки файлов к сделке (getchildren): {e}")