from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
import requests
import base64
import traceback
from io import BytesIO

app = FastAPI()

# .env
BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
FIELD_FILE = "UF_CRM_1740994275251"

class AttachRequest(BaseModel):
    deal_id: int
    folder_id: int

@app.post("/webhook/register_folder")
def register_folder(req: AttachRequest):
    try:
        deal_id = req.deal_id
        folder_id = req.folder_id

        print(f"📦 Вебхук получен: deal_id={deal_id}, folder_id={folder_id}")

        # 1. Получить файлы из папки
        folder_resp = requests.get(f"{BITRIX_WEBHOOK}/disk.folder.getchildren", params={"id": folder_id})
        folder_resp.raise_for_status()
        files = folder_resp.json().get("result", [])
        print(f"📂 Найдено файлов: {len(files)}")

        attached_count = 0
        tg_payloads = []

        for f in files:
            url = f.get("DOWNLOAD_URL")
            name = f.get("NAME") or "photo.jpg"
            if not url:
                continue
            resp = requests.get(url)
            if not resp.ok:
                continue

            file_bytes = resp.content
            mime = resp.headers.get("Content-Type", "")

            # 2. Прикрепить в сделку (если поле типа 'Файл')
            encoded = base64.b64encode(file_bytes).decode("utf-8")
            file_payload = {
                FIELD_FILE: {
                    "fileData": [name, encoded]
                }
            }
            update = requests.post(f"{BITRIX_WEBHOOK}/crm.deal.update", json={"id": deal_id, "fields": file_payload})
            if update.ok:
                print(f"✅ Файл прикреплён: {name}")
                attached_count += 1

            # 3. Для Telegram
            if mime.startswith("image"):
                tg_payloads.append((name, file_bytes))

        # 4. Отправка в Telegram (до 10 файлов)
        if TG_BOT_TOKEN and TG_CHAT_ID and tg_payloads:
            print("🚀 Отправка в Telegram...")
            send_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMediaGroup"
            chunks = [tg_payloads[i:i + 10] for i in range(0, len(tg_payloads), 10)]

            for chunk in chunks:
                media = []
                files_data = {}
                for idx, (fname, content) in enumerate(chunk):
                    key = f"photo{idx}"
                    media.append({"type": "photo", "media": f"attach://{key}"})
                    files_data[key] = (fname, BytesIO(content))
                requests.post(send_url, data={"chat_id": TG_CHAT_ID, "media": str(media).replace("'", '"')}, files=files_data)
                print(f"📤 Отправлено {len(chunk)} файлов в Telegram")

        return {"status": "ok", "attached": attached_count}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))