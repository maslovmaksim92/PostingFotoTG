import re
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def transform_bitrix_data(data):
    """
    Преобразует шаблонные переменные Bitrix24 вида {=Document.ID} или {=Сущность.Поле}
    в некоторые реальные значения (здесь – упрощённая логика).
    
    Пример:
      - '{=Document.ID}' → 'ID'
      - '{=Deal.UF_CUSTOM}' → 'UF_CUSTOM'
      - Прочие данные (списки, словари) обходятся рекурсивно.
    """
    if isinstance(data, dict):
        # Рекурсивно преобразуем каждое значение
        return {k: transform_bitrix_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [transform_bitrix_data(item) for item in data]
    elif isinstance(data, str) and data.startswith('{=') and data.endswith('}'):
        logger.info(f"Обнаружено шаблонное значение: {data}")
        # Пример: {=Document.ID}, {=Deal.Stage}
        # Извлекаем основную часть, без {= ... }
        # Если есть точка - берем последний сегмент, иначе весь
        inner = data[2:-1]  # убираем {= и }
        if '.' in inner:
            part = inner.split('.')[-1]
            logger.info(f"Шаблон '{data}' разбит по точке. Берём последнюю часть: '{part}'")
            return part
        else:
            logger.info(f"Шаблон '{data}' не содержит точку. Возвращаем всё: '{inner}'")
            return inner
    else:
        return data

@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    """
    Обработчик вебхука на /webhook/disk.
    1. Считывает сырые данные (request.data).
    2. Удаляет из JSON возможные комментарии (//... или /*...*/).
    3. Преобразует шаблонные переменные вида {=...}.
    4. Проверяет наличие folder_id, deal_id.
    """
    try:
        # Получаем сырые данные
        raw_data = request.data.decode('utf-8')
        logger.info(f"Received raw data: {raw_data}")

        # Удаляем однострочные комментарии // ...
        clean_data = re.sub(r'//.*', '', raw_data)
        # Удаляем многострочные комментарии /* ... */
        clean_data = re.sub(r'/\\*.*?\\*/', '', clean_data, flags=re.DOTALL)

        # Парсим JSON
        data = json.loads(clean_data)
        logger.info(f"Parsed JSON: {data}")

        # Преобразуем шаблонные переменные (например, {=Document.ID})
        transformed_data = transform_bitrix_data(data)
        logger.info(f"Transformed data: {transformed_data}")

        # Проверяем обязательные поля
        if not all(k in transformed_data for k in ['folder_id', 'deal_id']):
            logger.error(f"Отсутствуют обязательные поля в JSON: {transformed_data}")
            return jsonify({"error": "Missing required fields"}), 400

        # Здесь должна быть логика реальной обработки
        logger.info(f"folder_id={transformed_data['folder_id']}, deal_id={transformed_data['deal_id']}")

        # Пока возвращаем ответ для демонстрации
        return jsonify({
            "status": "success",
            "original_data": data,
            "transformed_data": transformed_data,
            "processing": "Implement your logic here"
        })

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
