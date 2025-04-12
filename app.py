from fastapi import FastAPI, HTTPException
from pathlib import Path
import os
import requests
import traceback
import time

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
FIELD_CODE = "UF_CRM_1740994275251"  # поле файл
FIELD_URL_CODE = "UF_CRM_FILE_IMAGE_URL"  # строка для подстановки ссылки в письмо

class BitrixClient:
    def __init__(self):
        if not BITRIX_WEBHOOK:
            raise ValueError("BITRIX_WEBHOOK not set")
        self.webhook = BITRIX_WEBHOOK

    def upload_file_to_folder(self, folder_id: int, filename: str, content: bytes):
        init_resp = requests.post(f"{self.webhook}/disk.folder.uploadfile", data={"id": folder_id})
        upload_url = init_resp.json().get("result", {}).get("uploadUrl")
        if not upload_url:
            raise HTTPException(status_code=400, detail=f"Не удалось получить uploadUrl: {init_resp.text}")

        files = {"file": (filename, content)}
        final_resp = requests.post(upload_url, files=files)
        file_json = final_resp.json().get("result", {})
        file_id = file_json.get("ID")
        if not file_id:
            raise HTTPException(status_code=400, detail=f"Не удалось получить ID из финального ответа: {final_resp.text}")

        return int(file_id), file_json.get("DOWNLOAD_URL")

    def update_deal_fields(self, deal_id: int, fields: dict) -> bool:
        payload = {"id": deal_id, "fields": fields}
        headers = {"Content-Type": "application/json"}
        response = requests.post(f"{self.webhook}/crm.deal.update", json=payload, headers=headers)
        print("crm.deal.update:", response.status_code, response.text)
        return response.json().get("result", False)

    def get_deal_field_files(self, deal_id: int, field_code: str):
        response = requests.get(f"{self.webhook}/crm.deal.get", params={"id": deal_id})
        data = response.json()
        return data.get("result", {}).get(field_code, None)

@app.post("/test-attach")
def test_attach():
    try:
        bitrix = BitrixClient()
        file_path = Path("image.png")
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Файл image.png не найден")

        with file_path.open("rb") as f:
            content = f.read()

        folder_id = 198874
        deal_id = 11720
        filename = f"image_{int(time.time())}.png"

        file_id, download_url = bitrix.upload_file_to_folder(folder_id, filename, content)

        success = bitrix.update_deal_fields(deal_id, {
            FIELD_CODE: [file_id],
            FIELD_URL_CODE: download_url
        })

        if not success:
            raise HTTPException(status_code=400, detail="Не удалось обновить сделку")

        return {"status": "ok", "file_id": file_id, "url": download_url}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health():
    return {"status": "ok"}

@app.get("/debug-deal-files")
def debug_deal_files():
    try:
        bitrix = BitrixClient()
        files = bitrix.get_deal_field_files(11720, FIELD_CODE)
        return {"field": FIELD_CODE, "value": files}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))