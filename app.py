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
        # Шаг 1 — получить uploadUrl
        init_resp = requests.post(f"{self.webhook}/disk.folder.uploadfile", data={"id": folder_id})
        print("Init upload response:", init_resp.text)
        init_json = init_resp.json()

        upload_url = init_json.get("result", {}).get("uploadUrl")
        if not upload_url:
            raise HTTPException(status_code=400, detail=f"Не удалось получить uploadUrl: {init_json}")

        # Шаг 2 — загрузка файла на uploadUrl
        files = {"file": (filename, content)}
        final_resp = requests.post(upload_url, files=files)
        print("Final upload response:", final_resp.text)
        final_json = final_resp.json()

        file_id = final_json.get("result", {}).get("ID")
        if not file_id:
            raise HTTPException(status_code=400, detail=f"Не удалось получить ID из финального ответа: {final_json}")

        return int(file_id)

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