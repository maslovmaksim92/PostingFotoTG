from fastapi import FastAPI, HTTPException
from pathlib import Path
import os
import requests
import traceback

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")

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
        file_id = final_resp.json().get("result", {}).get("ID")
        if not file_id:
            raise HTTPException(status_code=400, detail=f"Не удалось получить ID из финального ответа: {final_resp.text}")

        return int(file_id)

    def attach_file_to_deal(self, deal_id: int, field_code: str, file_id: int) -> bool:
        response = requests.post(f"{self.webhook}/crm.deal.update", data={
            "id": deal_id,
            f"fields[{field_code}][]": file_id  # Передаём как массив (multiple=true)
        })
        print("crm.deal.update response:", response.status_code, response.text)
        return response.json().get("result", False)

    def get_deal(self, deal_id: int) -> dict:
        response = requests.get(f"{self.webhook}/crm.deal.get", params={"id": deal_id})
        return response.json()

    def get_user_fields(self) -> dict:
        response = requests.get(f"{self.webhook}/crm.deal.userfield.list")
        return response.json()

@app.get("/")
def health():
    return {"status": "ok"}

@app.get("/debug-fields")
def debug_fields():
    try:
        bitrix = BitrixClient()
        return bitrix.get_user_fields()
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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
        field_code = "UF_CRM_1740994275251"

        file_id = bitrix.upload_file_to_folder(folder_id, "image.png", content)
        success = bitrix.attach_file_to_deal(deal_id, field_code, file_id)
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось прикрепить файл к сделке")

        return {"status": "ok", "file_id": file_id}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))