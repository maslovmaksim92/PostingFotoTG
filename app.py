from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from loguru import logger
import httpx
import base64
import os

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
FIELD_CODE = "UF_CRM_1740994275251"

class FolderPayload(BaseModel):
    deal_id: int
    folder_id: int

@app.post("/webhook/register_folder")
async def register_folder(payload: FolderPayload):
    try:
        deal_id = payload.deal_id
        folder_id = payload.folder_id
        logger.info(f"📥 Вебхук получен: deal={deal_id}, folder={folder_id}")

        async with httpx.AsyncClient() as client:
            # Получаем список файлов в папке
            resp = await client.post(f"{BITRIX_WEBHOOK}/disk.folder.getchildren", json={"id": folder_id})
            children = resp.json().get("result", [])
            file_list = [f for f in children if f.get("DOWNLOAD_URL")]

            if not file_list:
                logger.warning("⚠️ Нет файлов для загрузки")
                return {"status": "ok", "attached": []}

            file_data_list = []
            for f in file_list:
                url = f["DOWNLOAD_URL"]
                name = f.get("NAME", "file.jpg")
                file_resp = await client.get(url)
                if file_resp.status_code == 200:
                    content = base64.b64encode(file_resp.content).decode("utf-8")
                    file_data_list.append({"fileData": [name, content]})
                else:
                    logger.warning(f"❌ Ошибка скачивания {name}: {file_resp.status_code}")

            # Отправляем все файлы за один запрос
            update = await client.post(f"{BITRIX_WEBHOOK}/crm.deal.update", json={
                "id": deal_id,
                "fields": {
                    FIELD_CODE: file_data_list
                }
            })
            logger.debug(f"📤 Обновление сделки → {update.text}")

        logger.info(f"✅ Загружено файлов: {len(file_data_list)}")
        return {"status": "ok", "attached": [f['fileData'][0] for f in file_data_list]}

    except Exception as e:
        logger.exception("❌ Ошибка при обработке запроса")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/test")
async def test_webhook(request: Request):
    data = await request.json()
    return {"status": "ok", "echo": data}