from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import requests
import traceback
from io import BytesIO
import base64

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
FIELD_FILE = "UF_CRM_1740994275251"  # поле типа 'Файл'
TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

class AttachRequest(BaseModel):
    deal_id: int
    folder_id: int

class BitrixClient:
    def __init__(self):
        self.webhook = BITRIX_WEBHOOK

    def get_files_from_folder(self, folder_id: int):
        resp = requests.get(f"{self.webhook}/disk.folder.getchildren", params={"id": folder_id})
        return resp.json().get("result", [])

    def download_file_bytes(self, url: str) -> tuple[bytes, str]:
        resp = requests.get(url, stream=True)
        content_type = resp.headers.get("Content-Type", "")
        return resp.content, content_type

    def upload_to_crm_file_field(self, deal_id: int, name: str, file_bytes: bytes):
        encoded = base64.b64encode(file_bytes).decode("utf-8")
        file_data = {
            FIELD_FILE: {
                "fileData": [name, encoded]
            }
        }
        payload = {"id": deal_id, "fields": file_data}
        resp = requests.post(f"{self.webhook}/crm.deal.update", json=payload)
        print("Bitrix update resp:", resp.status_code, resp.text)
        return resp.ok

class TelegramClient:
    def __init__(self):
        self.token = TG_BOT_TOKEN
        self.chat_id = TG_CHAT_ID

    def send_photos(self, files: list[tuple[str, bytes]]) -> bool:
        if not self.token or not self.chat_id:
            return False
        endpoint = f"https://api.telegram.org/bot{self.token}/sendMediaGroup"
        CHUNK = 10
        success = True
        for i in range(0, len(files), CHUNK):
            media = []
            files_payload = {}
            for idx, (filename, content) in enumerate(files[i:i+CHUNK]):
                key = f"photo{idx}"
                files_payload[key] = (filename, BytesIO(content))
                media.append({"type": "photo", "media": f"attach://{key}"})
            resp = requests.post(endpoint, data={"chat_id": self.chat_id, "media": str(media).replace("'", '"')}, files=files_payload)
            success = success and resp.json().get("ok", False)
        return success

@app.post("/webhook/register_folder")
def webhook_register_folder(req: AttachRequest):
    try:
        bitrix = BitrixClient()
        telegram = TelegramClient()

        files = bitrix.get_files_from_folder(req.folder_id)
        attached = 0
        tg_photos = []

        for f in files:
            url = f.get("DOWNLOAD_URL")
            name = f.get("NAME") or "photo.jpg"
            if url:
                content, ctype = bitrix.download_file_bytes(url)
                if ctype.startswith("image"):
                    ok = bitrix.upload_to_crm_file_field(req.deal_id, name, content)
                    if ok:
                        attached += 1
                    tg_photos.append((name, content))

        if attached == 0:
            raise HTTPException(status_code=404, detail="Файлы не прикреплены")

        telegram.send_photos(tg_photos)

        return {"status": "ok", "files": attached}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))