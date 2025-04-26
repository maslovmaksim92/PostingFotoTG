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
        logger.debug(f"⬇️ Скачиваем файл: {name} из {download_url}")

        try:
            r = requests.get(download_url)
            r.raise_for_status()
            file_bytes = r.content

            init_url = f"{BITRIX_WEBHOOK}/disk.folder.uploadfile"
            init_resp = requests.post(init_url, files={
                "id": (None, str(folder_id)),
                "data[NAME]": (None, name),
                "generateUniqueName": (None, "Y")
            })
            init_resp.raise_for_status()
            logger.debug(f"📤 Ответ init: {init_resp.text}")
            upload_url = init_resp.json().get("result", {}).get("uploadUrl")
            if not upload_url:
                logger.warning(f"⚠️ Не удалось получить uploadUrl для {name}")
                continue

            upload_resp = requests.post(upload_url, files={
                "file": (name, file_bytes, "application/octet-stream")
            })
            upload_resp.raise_for_status()
            logger.debug(f"📥 Ответ upload {name}: {upload_resp.text}")

            upload_data = upload_resp.json()
            file_id = (
                upload_data.get("result", {}).get("ID") or
                upload_data.get("result", {}).get("file", {}).get("ID") or
                upload_data.get("ID") or
                upload_data.get("result")
            )

            if isinstance(file_id, int) or str(file_id).isdigit():
                logger.info(f"✅ Файл загружен: {name} → ID {file_id}")
                file_ids.append(int(file_id))
            else:
                logger.warning(f"⚠️ Нет ID в ответе после загрузки: {name}")

        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке файла {name}: {e}")

    if file_ids:
        payload = {"id": deal_id, "fields": {PHOTO_FIELD_CODE: file_ids}}
        update_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
        logger.debug(f"➡️ Обновляем сделку {deal_id}: {payload}")
        try:
            update_resp = requests.post(update_url, json=payload)
            update_resp.raise_for_status()
            logger.info(f"📎 Успешно прикреплены файлы к сделке {deal_id}: {file_ids}")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления сделки: {e}")

    return file_ids


async def attach_photos_if_cleaning_done(deal_id: int):
    logger.info(f"🔄 Проверка стадии для сделки {deal_id} перед прикреплением фото")
    fields = get_deal_fields(deal_id)
    stage_id = fields.get("STAGE_ID")

    if stage_id != "CLEAN_DONE":
        logger.info(f"⏭ Сделка {deal_id} не на стадии 'уборка завершена'. Текущая стадия: {stage_id}")
        return

    folder_id = fields.get(FOLDER_FIELD_CODE)
    if not folder_id:
        logger.warning(f"❗ У сделки {deal_id} нет папки с файлами (поле {FOLDER_FIELD_CODE})")
        return

    files = get_files_from_folder(folder_id)
    if not files:
        logger.info(f"ℹ️ Папка {folder_id} пуста для сделки {deal_id}, пропускаем прикрепление")
        return

    attach_media_to_deal(deal_id, files)
    logger.info(f"✅ Файлы из папки {folder_id} прикреплены к сделке {deal_id}")