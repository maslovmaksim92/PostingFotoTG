import re
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

def clean_bitrix_json(json_str):
    """Очищает JSON от комментариев и шаблонов Bitrix24"""
    json_str = re.sub(r'//.*|/\*.*?\*/', '', json_str, flags=re.DOTALL)  # Удаляем комментарии
    json_str = re.sub(r'\{=[^}]+\}', '"BITRIX_TEMPLATE"', json_str)      # Заменяем шаблоны
    return json_str

@app.route("/webhook/disk", methods=["POST"])
def handle_disk_webhook():
    try:
        # Очистка и парсинг JSON
        cleaned_data = clean_bitrix_json(request.data.decode('utf-8'))
        data = json.loads(cleaned_data)
        
        # Валидация
        if not all(k in data for k in ['folder_id', 'deal_id']):
            raise ValueError("Missing required fields")
            
        # --- ВСТАВЬТЕ СЮДА ВАШ ОРИГИНАЛЬНЫЙ КОД ОБРАБОТКИ ---
        # files = BitrixAPI.get_folder_files(data['folder_id'])
        # ... и вся остальная логика
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
