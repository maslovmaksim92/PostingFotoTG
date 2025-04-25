from services.optimize_upload import filter_valid_files

# Ваш существующий код...

def attach_media_to_deal(deal_id: int, files: List[Dict]) -> List[int]:
    logger.info(f"📎 Прикрепление файлов к сделке {deal_id} (финальная загрузка через uploadUrl)")

    # ✨ Новый шаг: фильтрация файлов
    files = filter_valid_files(files)

    file_ids = []
    fields = get_deal_fields(deal_id)
    folder_id = fields.get(FOLDER_FIELD_CODE)

    for file in files:
        name = file["name"][:50].replace(" ", "_")
        download_url = file["download_url"]
        logger.debug(f"⬇️ Скачиваем файл: {name} из {download_url}")

        try:
            r = requests.get(download_url)
            r.raise_for_status()
            file_bytes = r.content

            # Шаг 1 — получаем uploadUrl от Bitrix
            init_url = f"{BITRIX_WEBHOOK}/disk.folder.uploadfile"
            init_resp = requests.post(init_url, files={
                "id": (None, str(folder_id)),
                "data[NAME]": (None, name),
                "data[CREATED_BY]": (None, "1"),
                "generateUniqueName": (None, "Y")
            })
            init_resp.raise_for_status()
            logger.debug(f"📤 Ответ init: {init_resp.text}")
            upload_url = init_resp.json().get("result", {}).get("uploadUrl")

            if not upload_url:
                logger.warning(f"⚠️ Не удалось получить uploadUrl для {name}")
                continue

            # Шаг 2 — загрузка файла
            upload_resp = requests.post(upload_url, files={
                "file": (name, file_bytes, "application/octet-stream")
            })
            upload_resp.raise_for_status()
            logger.debug(f"📥 Ответ upload {name}: {upload_resp.text}")

            upload_data = upload_resp.json()
            file_id = (
                upload_data.get("result", {}).get("ID") or
                upload_data.get("result", {}).get("file", {}).get("ID") or
                upload_data.get("ID") or
                upload_data.get("result")
            )

            if isinstance(file_id, int) or str(file_id).isdigit():
                logger.info(f"✅ Файл загружен: {name} → ID {file_id}")
                file_ids.append(int(file_id))
            else:
                logger.warning(f"⚠️ Нет ID в ответе после загрузки: {name}")

        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке файла {name}: {e}")

    if file_ids:
        payload = {"id": deal_id, "fields": {PHOTO_FIELD_CODE: file_ids}}
        update_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
        logger.debug(f"➡️ Обновляем сделку {deal_id}: {payload}")
        try:
            update_resp = requests.post(update_url, json=payload)
            update_resp.raise_for_status()
            logger.info(f"📎 Успешно прикреплены файлы к сделке {deal_id}: {file_ids}")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления сделки: {e}")

    return file_ids