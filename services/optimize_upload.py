import os
import requests
from typing import List, Dict
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
MAX_FILE_SIZE_MB = 15  # Максимальный размер файла в мегабайтах
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "bmp"}

def is_valid_file(file: Dict) -> bool:
    """Проверяет, соответствует ли файл по размеру и формату."""
    file_size_mb = file.get("size", 0) / (1024 * 1024)
    name = file.get("name", "").lower()
    extension = name.split(".")[-1]

    if file_size_mb > MAX_FILE_SIZE_MB:
        logger.warning(f"⚠️ Файл {name} слишком большой: {file_size_mb:.2f} MB")
        return False

    if extension not in ALLOWED_EXTENSIONS:
        logger.warning(f"⚠️ Неподдерживаемый формат файла {name}: .{extension}")
        return False

    return True


def filter_valid_files(files: List[Dict]) -> List[Dict]:
    """Фильтрует валидные файлы для загрузки."""
    valid_files = [file for file in files if is_valid_file(file)]
    logger.info(f"✅ Прошло проверку: {len(valid_files)} файлов из {len(files)}")
    return valid_files