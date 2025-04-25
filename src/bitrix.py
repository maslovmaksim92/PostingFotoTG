import os
import requests
from typing import List, Dict
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
PHOTO_FIELD_CODE = os.getenv("FILE_FIELD_ID") or "UF_CRM_1740994275251"
FOLDER_FIELD_CODE = os.getenv("FOLDER_FIELD_ID") or "UF_CRM_1743273170850"
ADDRESS_FIELD_CODE = "UF_CRM_1669561599956"
MAX_FILE_SIZE_MB = 20  # Максимальный размер файла (20 МБ)

def get_deal_fields(deal_id: int) -> Dict:
    url = f"{BITRIX_WEBHOOK}/crm.deal.get"
    response = requests.post(url, json={"id": deal_id})
    response.raise_for_status()
    return response.json().get("result", {})

def get_address_from_deal(deal_id: int) -> str:
    fields = get_deal_fields(deal_id)
    raw = fields.get(ADDRESS_FIELD_CODE, "")
    return raw.split("|")[0] if "|" in raw else raw

def get_files_from_folder(folder_id: int) -> List[Dict]:
    url = f"{BITRIX_WEBHOOK}/disk.folder.getchildren"
    response = requests.post(url, json={"id": folder_id})
    response.raise_for_status()
    result = response.json().get("result", [])
    return [
        {
            "id": item["ID"],
            "name": item["NAME"],
            "size": item.get("SIZE", 0),
            "download_url": item["DOWNLOAD_URL"]
        }
        for item in result if item["TYPE"] == "file"
    ]

def attach_media_to_deal(deal_id: int, files: List[Dict]) -> List[int]:
    logger.info(f"📎 Прикрепление файлов к сделке {deal_id} (финальная загрузка через uploadUrl)")
    file_ids = []
    fields = get_deal_fields(deal_id)
    folder_id = fields.get(FOLDER_FIELD_CODE)

    for file in files:
        name = file["name"][:50].replace(" ", "_")
        download_url = file["download_url"]
        file_size_mb = file.get("size", 0) / (1024 * 1024)

        if file_size_mb > MAX_FILE_SIZE_MB:
            logger.warning(f"⚠️ Пропущен файл {name}: размер {file_size_mb:.2f} МБ превышает лимит {MAX_FILE_SIZE_MB} МБ")
            continue

        logger.debug(f"⬇️ Скачиваем файл: {name} из {download_url}")

        try:
            r = requests.get(download_url)
            r.raise_for_status()
            file_bytes = r.content

            # 1. Инициализация uploadUrl
            init_url = f"{BITRIX_WEBHOOK}/disk.folder.uploadfile"
            init_resp = requests.post(init_url, files={
                "id": (None, str(folder_id)),
                "data[NAME]": (None, name),
                "data[CREATED_BY]": (None, "1"),
                "generateUniqueName": (None, "Y")
            })
            init_resp.raise_for_status()
            upload_url = init_resp.json().get("result", {}).get("uploadUrl")

            if not upload_url:
                logger.warning(f"⚠️ Не удалось получить uploadUrl для {name}")
                continue

            # 2. Фактическая загрузка файла
            upload_resp = requests.post(upload_url, files={
                "file": (name, file_bytes, "application/octet-stream")
            })
            upload_resp.raise_for_status()
            upload_data = upload_resp.json()

            file_id = (
                upload_data.get("result", {}).get("ID") or
                upload_data.get("result", {}).get("file", {}).get("ID") or
                upload_data.get("ID")
            )

            if isinstance(file_id, int) or str(file_id).isdigit():
                logger.info(f"✅ Файл успешно загружен: {name} → ID {file_id}")
                file_ids.append(int(file_id))
            else:
                logger.warning(f"⚠️ Нет ID в ответе после загрузки: {name}")

        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке файла {name}: {e}")

    if file_ids:
        payload = {"id": deal_id, "fields": {PHOTO_FIELD_CODE: file_ids}}
        update_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
        try:
            update_resp = requests.post(update_url, json=payload)
            update_resp.raise_for_status()
            logger.info(f"📎 Файлы прикреплены к сделке {deal_id}: {file_ids}")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления сделки {deal_id}: {e}")

    return file_ids