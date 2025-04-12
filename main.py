from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")

class AttachRequest(BaseModel):
    deal_id: int
    file_id: int
    field_code: str = "UF_CRM_FILE"

@app.post("/attach-file")
def attach_file(req: AttachRequest):
    if not BITRIX_WEBHOOK:
        raise HTTPException(status_code=500, detail="Bitrix webhook is not set")

    # Получаем информацию о файле
    file_info = requests.get(f"{BITRIX_WEBHOOK}/disk.file.get", params={"id": req.file_id}).json()
    if "result" not in file_info:
        raise HTTPException(status_code=400, detail=f"Failed to get file info: {file_info}")

    download_url = file_info["result"].get("DOWNLOAD_URL")
    if not download_url:
        raise HTTPException(status_code=400, detail="No download URL found")

    # Скачиваем файл
    file_content = requests.get(download_url).content

    # Загружаем файл в Bitrix (через временное поле)
    files = {"file": ("attachment.jpg", file_content)}
    upload_resp = requests.post(f"{BITRIX_WEBHOOK}/disk.folder.uploadfile", files=files, data={"id": 1}).json()
    if "result" not in upload_resp:
        raise HTTPException(status_code=400, detail=f"File upload failed: {upload_resp}")

    uploaded_file_id = upload_resp["result"]["ID"]

    # Прикрепляем файл к сделке
    update = requests.post(f"{BITRIX_WEBHOOK}/crm.deal.update", data={
        "id": req.deal_id,
        f"fields[{req.field_code}]": uploaded_file_id
    }).json()

    if not update.get("result"):
        raise HTTPException(status_code=400, detail=f"Failed to attach file to deal: {update}")

    return {"status": "ok", "file_id": uploaded_file_id}