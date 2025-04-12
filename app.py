@app.post("/attach-ids")
def attach_file_ids(req: AttachRequest):
    try:
        bitrix = BitrixClient()
        files = bitrix.get_files_from_folder(req.folder_id)
        file_ids = [f["ID"] for f in files if f.get("ID")]

        if not file_ids:
            raise HTTPException(status_code=404, detail="Файлы в папке не найдены")

        updated = bitrix.update_deal_fields(req.deal_id, {
            FIELD_FILE: file_ids
        })

        if not updated:
            raise HTTPException(status_code=500, detail="crm.deal.update не сработал")

        return {"status": "ok", "file_ids": file_ids, "count": len(file_ids)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))