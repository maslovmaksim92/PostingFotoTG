import os
import requests
from typing import List, Dict
from datetime import datetime
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
    if "|" in raw:
        address = raw.split("|")[0]
    else:
        address = raw
    address = address.replace(",", "").replace("|", "").replace("\\", "").strip()
    return address

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
    logger.info(f"📎 Загрузка файлов через disk.folder.uploadfile с коррекцией ссылок для сделки {deal_id}")
    uploaded_file_ids = []
    download_urls = []

    if not files:
        logger.warning(f"⚠️ Нет файлов для прикрепления в сделке {deal_id}")
        return []

    folder_id = get_deal_fields(deal_id).get(FOLDER_FIELD_CODE)
    address = get_address_from_deal(deal_id)
    today_str = datetime.now().strftime("%Y-%m-%d")

    for idx, file in enumerate(files):
        download_url = file.get("download_url")

        # Генерируем новое имя файла
        new_name = f"уборка-{address}-{today_str} ваш дом-{idx + 1}.jpg"

        if download_url:
            # Корректируем ссылку перед скачиванием
            if "&auth=" in download_url:
                parts = download_url.split("&auth=")
                if len(parts) == 2:
                    download_url = parts[0] + "?auth=" + parts[1]

            try:
                response = requests.get(download_url)
                response.raise_for_status()
                file_bytes = response.content

                # Этап 1: инициализация загрузки
                init_upload_url = f"{BITRIX_WEBHOOK}/disk.folder.uploadfile"
                init_resp = requests.post(init_upload_url, data={
                    "id": folder_id,
                    "data[NAME]": new_name,
                    "generateUniqueName": "Y"
                })
                init_resp.raise_for_status()
                upload_url = init_resp.json().get("result", {}).get("uploadUrl")

                if not upload_url:
                    logger.error(f"❌ Не получен uploadUrl для файла {new_name}")
                    continue

                # Этап 2: отправка файла на uploadUrl
                upload_resp = requests.post(upload_url, files={
                    "file": (new_name, file_bytes, "application/octet-stream")
                })
                upload_resp.raise_for_status()
                upload_data = upload_resp.json()

                uploaded_file_id = (
                    upload_data.get("result", {}).get("ID") or
                    upload_data.get("result", {}).get("file", {}).get("ID")
                )

                if uploaded_file_id:
                    uploaded_file_ids.append(int(uploaded_file_id))
                    download_urls.append(download_url)
                    logger.info(f"✅ Файл успешно загружен: {new_name} → ID {uploaded_file_id}")
                else:
                    logger.error(f"❌ Не получен ID загруженного файла для {new_name}")

            except Exception as e:
                logger.error(f"❌ Ошибка при загрузке файла {new_name}: {e}")

    if uploaded_file_ids:
        payload = {"id": deal_id, "fields": {PHOTO_FIELD_CODE: uploaded_file_ids}}
        update_url = f"{BITRIX_WEBHOOK}/crm.deal.update"
        try:
            update_resp = requests.post(update_url, json=payload)
            update_resp.raise_for_status()
            logger.info(f"✅ Файлы успешно прикреплены к сделке {deal_id}: {uploaded_file_ids}")
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении сделки при прикреплении файлов: {e}")

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

    return uploaded_file_ids