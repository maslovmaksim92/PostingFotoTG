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
        if not BITRIX_WEBHOOK:
            raise ValueError("BITRIX_WEBHOOK not set")
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
            print("Telegram: токен или chat_id не заданы")
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
        html_blocks = []
        tg_photos = []

        for f in files:
            fid = f.get("ID")
            name = f.get("NAME") or "photo.jpg"
            ext = os.path.splitext(name)[-1].lower()
            if fid and ext in ALLOWED_EXTENSIONS:
                url = bitrix.get_download_url(fid)
                if url:
                    content, ctype = bitrix.download_file_bytes(url)
                    if ctype.startswith("image"):
                        file_ids.append(fid)
                        html_blocks.append(f'<img src="{url}" style="max-width:100%;margin-bottom:10px;"/>')
                        tg_photos.append((name, content))

        if not file_ids:
            raise HTTPException(status_code=404, detail="Файлы есть, но ссылки не получены")

        bitrix.update_deal_fields(req.deal_id, {
            FIELD_FILE: file_ids,
            FIELD_HTML: "\n".join(html_blocks)
        })

        telegram.send_photos(tg_photos)

        return {"status": "ok", "files_attached": len(file_ids)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))