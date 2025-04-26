import os
import base64
import requests
from loguru import logger

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")


def upload_file_to_bitrix(file_path: str, folder_id: int) -> dict:
    try:
        file_name = os.path.basename(file_path)
        with open(file_path, "rb") as file:
            encoded_file = base64.b64encode(file.read()).decode("utf-8")

        url = f"{BITRIX_WEBHOOK}/disk.folder.uploadfile"
        data = {
            "id": folder_id,
            "data": {"NAME": file_name},
            "fileContent": [file_name, encoded_file],
        }
        response = requests.post(url, json=data)
        result = response.json()

        if not result.get("result"):
            logger.error(f"❌ Ошибка загрузки файла {file_name}: {result}")
        else:
            logger.info(f"✅ Файл {file_name} успешно загружен в Bitrix")

        return result

    except Exception as e:
        logger.exception(f"❌ Исключение при загрузке файла {file_path}: {e}")
        return {"error": str(e)}