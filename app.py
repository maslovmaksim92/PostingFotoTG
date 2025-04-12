from fastapi import FastAPI, HTTPException
from pathlib import Path
import os
import requests

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
        json_data = response.json()
        if "result" in json_data:
            return int(json_data["result"]["ID"])
        return None

    def attach_file_to_deal(self, deal_id: int, field_code: str, file_id: int) -> bool:
        response = requests.post(f"{self.webhook}/crm.deal.update", data={
            "id": deal_id,
            f"fields[{field_code}]": file_id
        })
        return response.json().get("result", False)

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/test-attach")
def test_attach():
    print("Запущен эндпоинт /test-attach")
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
    if not file_id:
        raise HTTPException(status_code=400, detail="Ошибка загрузки файла в папку Bitrix")

    success = bitrix.attach_file_to_deal(deal_id, field_code, file_id)
    if not success:
        raise HTTPException(status_code=400, detail="Не удалось прикрепить файл к сделке")

    return {"status": "ok", "file_id": file_id}