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
        files = {"file": (filename, content)}
        response = requests.post(f"{self.webhook}/disk.folder.uploadfile", data={"id": folder_id}, files=files)
        print("Upload file response:", response.status_code, response.text)
        json_data = response.json()
        if "result" in json_data and "ID" in json_data["result"]:
            return int(json_data["result"]["ID"])
        raise HTTPException(status_code=400, detail=f"Ошибка Bitrix: {json_data}")

    def attach_file_to_deal(self, deal_id: int, field_code: str, file_id: int) -> bool:
        response = requests.post(f"{self.webhook}/crm.deal.update", data={
            "id": deal_id,
            f"fields[{field_code}]": file_id
        })
        print("Attach file response:", response.text)
        return response.json().get("result", False)

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/test-attach")
def test_attach():
    try:
        print("=== /test-attach called ===")
        bitrix = BitrixClient()

        file_path = Path("image.png")
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Файл image.png не найден")

        with file_path.open("rb") as f:
            content = f.read()

        folder_id = 198874
        deal_id = 11720
        field_code = "UF_CRM_1744310845527"

        file_id = bitrix.upload_file_to_folder(folder_id, "image.png", content)
        success = bitrix.attach_file_to_deal(deal_id, field_code, file_id)
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось прикрепить файл к сделке")

        return {"status": "ok", "file_id": file_id}
    except Exception as e:
        print("ERROR:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))