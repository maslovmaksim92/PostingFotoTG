import json
from datetime import datetime

def log_bitrix_payload(payload: dict):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    with open(f"logs/bitrix_webhook_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)