from fastapi import FastAPI, Request
from pydantic import BaseModel
from loguru import logger
import httpx
import os

BOT_TOKEN = os.getenv("TG_GITHUB_BOT")
CHAT_ID = os.getenv("TG_CHAT_ID")
BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")

app = FastAPI()


class FolderWebhook(BaseModel):
    deal_id: int
    folder_id: int


@app.post("/webhook/register_folder")
async def register_folder(data: FolderWebhook):
    logger.info(f"\U0001F4E5 Получен вебхук: deal={data.deal_id}, folder={data.folder_id}")

    async with httpx.AsyncClient() as client:
        # Получаем список файлов из папки
        r = await client.post(
            f"{BITRIX_WEBHOOK}/disk.folder.getchildren",
            json={"id": data.folder_id},
        )
        files = r.json().get("result", [])
        file_ids = [f["ID"] for f in files if f.get("ID")]
        logger.info(f"\U0001F5CE Найдено файлов: {len(file_ids)} — {file_ids}")

        if not file_ids:
            return {"status": "ok", "files": 0}

        # Прикрепляем к сделке
        await client.post(
            f"{BITRIX_WEBHOOK}/crm.deal.update",
            json={
                "id": data.deal_id,
                "fields": {"UF_CRM_1740994275251": file_ids},
            },
        )
        logger.info(f"✅ Файлы успешно прикреплены к сделке {data.deal_id}")

        # Отправляем в ТГ пачками по 10
        chunks = [file_ids[i:i+10] for i in range(0, len(file_ids), 10)]
        for group in chunks:
            media = [
                {
                    "type": "document",
                    "media": f"https://vas-dom.bitrix24.ru/rest/1/bi0kv4y9ym8quxpa/disk.file.download?fileId={fid}",
                }
                for fid in group
            ]
            await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup",
                json={"chat_id": CHAT_ID, "media": media},
            )
    return {"status": "ok", "files_attached": len(file_ids)}