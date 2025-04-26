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
FILE_LINKS_FIELD_CODE = "UF_CRM_1745671890168"

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
    logger.debug(f"🔍 Найдено файлов в папке {folder_id}: {len(result)} файлов")
    return [
        {
            "id": item["ID"],
            "name": item["NAME"],
            "size": item.get("SIZE", 0),
            "download_url": item.get("DOWNLOAD_URL")
        }
        for item in result if item["TYPE"] == "file"
    ]

def attach_media_to_deal(deal_id: int, files: List[Dict]) -> List[int]:
    logger.info(f"📎 Прикрепление файлов к сделке {deal_id} через скачивание и загрузку")
    file_data_list = []
    download_urls = []

    if not files:
        logger.warning(f"⚠️ Нет файлов для прикрепления в сделке {deal_id}")
        return []

    for file in files:
        name = file.get("name", "file.jpg")
        download_url = file.get("download_url")

        if download_url:
            try:
                response = requests.get(download_url)
                response.raise_for_status()
                file_bytes = response.content

                # Добавляем файл в список для обновления сделки
                file_data_list.append({
                    "fileContent": [name, file_bytes]
                })
                download_urls.append(download_url)
                logger.debug(f"⬇️ Скачан файл: {name}")

            except Exception as e:
                logger.error(f"❌ Ошибка скачивания файла {name}: {e}")

    if file_data_list:
        payload = {
            "id": deal_id,
            "fields": {
                PHOTO_FIELD_CODE: file_data_list
            }
        }
        update_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
        logger.debug(f"➡️ Обновляем сделку {deal_id} загрузкой файлов.")
        try:
            update_resp = requests.post(update_url, files={
                "id": (None, str(deal_id)),
                "fields[{}][0][fileContent]".format(PHOTO_FIELD_CODE): (file_data_list[0]['fileContent'][0], file_data_list[0]['fileContent'][1], 'application/octet-stream')
            })
            update_resp.raise_for_status()
            logger.info(f"✅ Файлы физически прикреплены к сделке {deal_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления сделки при загрузке файлов: {e}")

    if download_urls:
        payload_links = {
            "id": deal_id,
            "fields": {
                FILE_LINKS_FIELD_CODE: "\n".join(download_urls)
            }
        }
        update_links_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
        try:
            links_resp = requests.post(update_links_url, json=payload_links)
            links_resp.raise_for_status()
            logger.info(f"🔗 Ссылки на файлы сохранены в сделке {deal_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения ссылок на файлы: {e}")

    return []