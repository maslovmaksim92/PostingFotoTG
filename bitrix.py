import os
import requests
import base64
from typing import List, Dict
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
PHOTO_FIELD_CODE = "UF_CRM_1740994275251"
FOLDER_FIELD_CODE = "UF_CRM_1743273170850"
ADDRESS_FIELD_CODE = "UF_CRM_1669561599956"


def get_deal_fields(deal_id: int) -> Dict:
    url = f"{BITRIX_WEBHOOK}/crm.deal.get"
    response = requests.post(url, json={"id": deal_id})
    response.raise_for_status()
    data = response.json()
    logger.info(f"📋 Получены поля сделки {deal_id}")
    return data.get("result", {})


def get_address_from_deal(deal_id: int) -> str:
    fields = get_deal_fields(deal_id)
    raw = fields.get(ADDRESS_FIELD_CODE, "")
    address = raw.split("|")[0] if "|" in raw else raw
    logger.info(f"📍 Адрес сделки {deal_id}: {address}")
    return address


def get_files_from_folder(folder_id: int) -> List[Dict]:
    url = f"{BITRIX_WEBHOOK}/disk.folder.getchildren"
    response = requests.post(url, json={"id": folder_id})
    response.raise_for_status()
    result = response.json().get("result", [])

    files = []
    for item in result:
        if item["TYPE"] == "file":
            files.append({
                "id": item["ID"],
                "name": item["NAME"],
                "size": item.get("SIZE", 0),
                "download_url": item["DOWNLOAD_URL"]
            })
    logger.info(f"✅ Найдено файлов в папке {folder_id}: {len(files)}")
    return files


def attach_media_to_deal(deal_id: int, files: List[Dict]) -> List[int]:
    uploaded_file_ids = []

    for file in files:
        name = file["name"][:50].replace(" ", "_")
        url = file["download_url"]

        logger.debug(f"📤 Upload payload: {name} (size: {file.get('size', 0)} bytes)")
        try:
            r = requests.get(url)
            r.raise_for_status()
            b64 = base64.b64encode(r.content).decode("utf-8")

            upload_url = f"{BITRIX_WEBHOOK}/disk.folder.uploadfile"
            upload_resp = requests.post(upload_url, json={
                "id": deal_id,
                "data": {"NAME": name, "CREATED_BY": 1},
                "fileContent": [name, b64]
            })
            upload_resp.raise_for_status()
            result = upload_resp.json().get("result", {})
            file_id = result.get("ID")
            if file_id:
                uploaded_file_ids.append(int(file_id))
            else:
                logger.error(f"⚠️ Нет ID файла в ответе Bitrix")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки файла в Bitrix: {e}")

    # Прикрепление к сделке
    if uploaded_file_ids:
        update_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
        payload = {"id": deal_id, "fields": {PHOTO_FIELD_CODE: uploaded_file_ids}}
        logger.debug(f"➡️ CRM PAYLOAD (uploadfile): {payload}")
        update_resp = requests.post(update_url, json=payload)
        update_resp.raise_for_status()
        logger.debug(f"✅ Ответ от Bitrix: {update_resp.json()}")
        logger.info(f"📎 Прикреплены файлы к сделке {deal_id}: {uploaded_file_ids}")

    return uploaded_file_ids