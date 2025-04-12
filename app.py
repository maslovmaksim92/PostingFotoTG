from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import requests
import traceback

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
FIELD_FILE = "UF_CRM_1740994275251"
FIELD_HTML = "UF_CRM_PHOTO_HTML_BLOCK"
TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

class AttachRequest(BaseModel):
    deal_id: int
    folder_id: int

class BitrixClient:
    def __init__(self):
        if not BITRIX_WEBHOOK:
            raise ValueError("BITRIX_WEBHOOK not set")
        self.webhook = BITRIX_WEBHOOK

    def get_files_from_folder(self, folder_id: int):
        resp = requests.get(f"{self.webhook}/disk.folder.getchildren", params={"id": folder_id})
        return resp.json().get("result", [])

    def get_public_link(self, file_id: int) -> str:
        resp = requests.get(f"{self.webhook}/disk.file.getpubliclink", params={"id": file_id})
        return resp.json().get("result", {}).get("LINK", "")

    def update_deal_fields(self, deal_id: int, fields: dict) -> bool:
        payload = {"id": deal_id, "fields": fields}
        resp = requests.post(f"{self.webhook}/crm.deal.update", json=payload)
        return resp.json().get("result", False)

    def get_deal_fields(self, deal_id: int) -> dict:
        resp = requests.get(f"{self.webhook}/crm.deal.get", params={"id": deal_id})
        return resp.json().get("result", {})

class TelegramClient:
    def __init__(self):
        self.token = TG_BOT_TOKEN
        self.chat_id = TG_CHAT_ID

    def send_photos(self, urls: list[str]) -> bool:
        if not self.token or not self.chat_id:
            print("Telegram: токен или chat_id не заданы")
            return False

        endpoint = f"https://api.telegram.org/bot{self.token}/sendMediaGroup"
        CHUNK = 10
        success = True
        for i in range(0, len(urls), CHUNK):
            media = [{"type": "photo", "media": url} for url in urls[i:i+CHUNK]]
            resp = requests.post(endpoint, json={"chat_id": self.chat_id, "media": media})
            print("TG resp:", resp.status_code, resp.text)
            success = success and resp.json().get("ok", False)
        return success

@app.post("/attach-folder")
def attach_folder(req: AttachRequest):
    try:
        bitrix = BitrixClient()
        telegram = TelegramClient()

        files = bitrix.get_files_from_folder(req.folder_id)

        file_ids = []
        public_urls = []
        html_blocks = []

        for f in files:
            fid = f.get("ID")
            if fid:
                public_url = bitrix.get_public_link(fid)
                if public_url:
                    file_ids.append(fid)
                    public_urls.append(public_url)
                    html_blocks.append(f'<img src="{public_url}" style="max-width:100%;margin-bottom:10px;"/>')

        if not file_ids:
            raise HTTPException(status_code=404, detail="Файлы найдены, но не удалось получить ссылки")

        bitrix.update_deal_fields(req.deal_id, {
            FIELD_FILE: file_ids,
            FIELD_HTML: "\n".join(html_blocks)
        })

        telegram.send_photos(public_urls)

        return {"status": "ok", "files_attached": len(file_ids)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))