@app.post("/webhook/register_folder")
def webhook_register_folder(req: AttachRequest):
    try:
        bitrix = BitrixClient()
        telegram = TelegramClient()

        files = bitrix.get_files_from_folder(req.folder_id)
        file_ids = []
        tg_photos = []

        for f in files:
            url = f.get("DOWNLOAD_URL")
            name = f.get("NAME") or "photo.jpg"
            if url:
                content, ctype = bitrix.download_file_bytes(url)
                if ctype.startswith("image"):
                    file_ids.append(f["ID"])
                    tg_photos.append((name, content))

        if not file_ids:
            raise HTTPException(status_code=404, detail="Нет изображений в папке")

        # Обновляем поле привязки к файлам (Диск)
        bitrix.update_deal_fields(req.deal_id, {
            FIELD_FILE: file_ids  # напрямую массив ID файлов с Диска
        })

        telegram.send_photos(tg_photos)

        return {"status": "ok", "files": len(file_ids)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))