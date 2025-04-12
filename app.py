@app.get("/deal-files")
def get_deal_file_urls(deal_id: int, folder_id: int):
    try:
        bitrix = BitrixClient()
        files = bitrix.get_files_from_folder(folder_id)
        urls = []

        for f in files:
            fid = f.get("ID")
            if fid:
                url = bitrix.get_download_url(fid)
                if url:
                    urls.append(url)

        return {"deal_id": deal_id, "folder_id": folder_id, "urls": urls}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))