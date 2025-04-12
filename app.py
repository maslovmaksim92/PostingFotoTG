from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import httpx
import traceback

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
TG_BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

app = FastAPI()

class FolderPayload(BaseModel):
    deal_id: int
    folder_id: int

@app.post("/webhook/register_folder")
async def register_folder(payload: FolderPayload):
    try:
        deal_id = payload.deal_id
        folder_id = payload.folder_id

        print(f"📦 [REGISTER_FOLDER] Получен вебхук → deal={deal_id}, folder={folder_id}")

        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BITRIX_WEBHOOK}/disk.folder.getchildren",
                json={"id": folder_id}
            )
            r.raise_for_status()
            files = r.json().get("result", [])

            file_ids = [f["ID"] for f in files if f.get("ID")]
            print(f"📎 Файлы в папке: {file_ids}")

            if file_ids:
                await client.post(
                    f"{BITRIX_WEBHOOK}/crm.deal.update",
                    json={
                        "id": deal_id,
                        "fields": {
                            "UF_CRM_1740994275251": file_ids
                        }
                    }
                )
                print("✅ Прикреплены к сделке")

                for file in files:
                    if "DOWNLOAD_URL" in file:
                        url = file["DOWNLOAD_URL"]
                        await client.post(
                            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto",
                            data={"chat_id": TG_CHAT_ID, "photo": url}
                        )
                print("🚀 Отправлено в Telegram")

        return {"status": "ok", "files_attached": len(file_ids)}

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})