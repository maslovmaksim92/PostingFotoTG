from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import requests
import traceback
from io import BytesIO
import base64

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
FIELD_FILE = "UF_CRM_1740994275251"

class AttachRequest(BaseModel):
    deal_id: int
    folder_id: int

class BitrixClient:
    def __init__(self):
        self.webhook = BITRIX_WEBHOOK

    def get_files_from_folder(self, folder_id: int):
        resp = requests.get(f"{self.webhook}/disk.folder.getchildren", params={"id": folder_id})
        return resp.json().get("result", [])

    def download_file_and_encode(self, url: str) -> tuple[str, str]:
        r = requests.get(url, stream=True)
        filename = url.split("?")[0].split("/")[-1]
        encoded = base64.b64encode(r.content).decode("utf-8")
        return filename, encoded

    def update_deal_with_file_data(self, deal_id: int, field_code: str, filedata: list[tuple[str, str]]) -> bool:
        files_payload = [{"fileData": [name, content]} for name, content in filedata]
        payload = {
            "id": deal_id,
            "fields": {
                field_code: files_payload
            }
        }
        resp = requests.post(f"{self.webhook}/crm.deal.update", json=payload)
        print("crm.deal.update:", resp.status_code, resp.text)
        return resp.json().get("result", False)

@app.post("/attach-ids")
def attach_ids(req: AttachRequest):
    try:
        bitrix = BitrixClient()
        files = bitrix.get_files_from_folder(req.folder_id)
        filedata = []

        for f in files:
            url = f.get("DOWNLOAD_URL")
            if url:
                name, encoded = bitrix.download_file_and_encode(url)
                filedata.append((name, encoded))

        if not filedata:
            raise HTTPException(status_code=404, detail="Нет файлов для прикрепления")

        success = bitrix.update_deal_with_file_data(req.deal_id, FIELD_FILE, filedata)
        if not success:
            raise HTTPException(status_code=500, detail="Не удалось обновить сделку")

        return {"status": "ok", "files_attached": len(filedata)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))