import os
import requests
import base64
from typing import List, Dict
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
PHOTO_FIELD_CODE = os.getenv("FILE_FIELD_ID") or "UF_CRM_1740994275251"
FOLDER_FIELD_CODE = os.getenv("FOLDER_FIELD_ID") or "UF_CRM_1743273170850"
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
    from bitrix import get_deal_fields
    logger.info(f"📎 Начинаем скачивание и прикрепление файлов к сделке {deal_id}")
    file_ids = []

    # Получаем ID папки из сделки
    fields = get_deal_fields(deal_id)
    folder_id = fields.get(FOLDER_FIELD_CODE)

    for file in files:
        name = file["name"][:50].replace(" ", "_")
        url = file["download_url"]
        logger.debug(f"⬇️ Скачиваем файл: {name} из {url}")

        try:
            r = requests.get(url)
            r.raise_for_status()
            file_bytes = r.content

            upload_url = f"{BITRIX_WEBHOOK}/disk.folder.uploadfile?attach=Y"
            files_data = {
                'id': (None, str(folder_id)),
                'data[NAME]': (None, name),
                'data[CREATED_BY]': (None, '1'),
                'file': (name, file_bytes)
            }

            upload_resp = requests.post(upload_url, files=files_data)
            upload_resp.raise_for_status()
            result = upload_resp.json().get("result", {})
            file_id = result.get("ID")

            if file_id:
                logger.info(f"✅ Загружен файл: {name} → ID: {file_id}")
                file_ids.append(file_id)
            else:
                logger.warning(f"⚠️ Нет ID файла в ответе Bitrix: {name}")

        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке файла {name}: {e}")

    # Прикрепляем все полученные ID файлов
    if file_ids:
        update_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
        payload = {"id": deal_id, "fields": {PHOTO_FIELD_CODE: file_ids}}
        logger.debug(f"➡️ Отправляем payload для прикрепления: {payload}")

        try:
            resp = requests.post(update_url, json=payload)
            resp.raise_for_status()
            logger.info(f"📎 Успешно прикреплены файлы к сделке {deal_id}: {file_ids}")
        except Exception as e:
            logger.error(f"❌ Ошибка прикрепления к сделке {deal_id}: {e}")

    return file_ids
