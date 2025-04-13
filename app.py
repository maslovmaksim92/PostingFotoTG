import os
import base64
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from loguru import logger
import httpx

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
FIELD_CODE = "UF_CRM_1740994275251"


class FolderPayload(BaseModel):
    deal_id: int
    folder_id: int


@app.post("/webhook/test")
async def test_webhook(payload: dict):
    logger.info(f"🔥 Тестовый вебхук получен: {payload}")
    return {"status": "ok", "echo": payload}


@app.post("/webhook/register_folder")
async def register_folder(payload: FolderPayload):
    try:
        deal_id = payload.deal_id
        folder_id = payload.folder_id
        logger.info(f"📥 Вебхук получен: deal={deal_id}, folder={folder_id}")

        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{BITRIX_WEBHOOK}/disk.folder.getchildren", json={"id": folder_id})
            children = resp.json().get("result", [])
            file_list = [f for f in children if f.get("DOWNLOAD_URL")]

            if not file_list:
                logger.warning("⚠️ Нет файлов для загрузки")
                return {"status": "ok", "attached": []}

            attached = []
            for f in file_list:
                url = f["DOWNLOAD_URL"]
                name = f.get("NAME", "file.jpg")
                file_resp = await client.get(url)
                if file_resp.status_code == 200:
                    content = base64.b64encode(file_resp.content).decode("utf-8")
                    update = await client.post(f"{BITRIX_WEBHOOK}/crm.deal.update", json={
                        "id": deal_id,
                        "fields": {
                            FIELD_CODE: {
                                "fileData": [name, content]
                            }
                        }
                    })
                    logger.debug(f"📤 Загрузка файла {name} → {update.text}")
                    attached.append(name)
                else:
                    logger.warning(f"❌ Ошибка загрузки файла {name}: {file_resp.status_code}")

        logger.info(f"✅ Загружено файлов: {len(attached)} — {attached}")
        return {"status": "ok", "attached": attached}

    except Exception as e:
        logger.exception("❌ Ошибка при обработке вебхука")
        raise HTTPException(status_code=500, detail=str(e))