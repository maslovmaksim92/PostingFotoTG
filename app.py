from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import requests
import traceback
from io import BytesIO

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
FIELD_FILE = "UF_CRM_1740994275251"
FIELD_HTML = "UF_CRM_PHOTO_HTML_BLOCK"
TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}

class AttachRequest(BaseModel):
    deal_id: int
    folder_id: int

class BitrixClient:
    def __init__(self):
        self.webhook = BITRIX_WEBHOOK

    def get_files_from_folder(self, folder_id: int):
        resp = requests.get(f"{self.webhook}/disk.folder.getchildren", params={"id": folder_id})
        return resp.json().get("result", [])

    def get_download_url(self, file_id: int) -> str:
        info = requests.get(f"{self.webhook}/disk.file.get", params={"id": file_id})
        return info.json().get("result", {}).get("DOWNLOAD_URL", "")

    def download_file_bytes(self, url: str) -> tuple[bytes, str]:
        resp = requests.get(url, stream=True)
        content_type = resp.headers.get("Content-Type", "")
        return resp.content, content_type

    def update_deal_fields(self, deal_id: int, fields: dict) -> bool:
        payload = {"id": deal_id, "fields": fields}
        resp = requests.post(f"{self.webhook}/crm.deal.update", json=payload)
        return resp.json().get("result", False)

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