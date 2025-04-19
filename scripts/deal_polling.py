import requests
import os
import json
from services.stage_resolver import stage_resolver
from services.deal_notifier import notify_deal_complete
from pathlib import Path

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
STORAGE_FILE = Path(".deal_stage_cache.json")


class DealWatcher:
    def __init__(self):
        self.stage_id_done = stage_resolver.get_stage_id_by_name("Уборка завершена")
        self.last_known: dict[str, str] = self._load()

    def _load(self):
        if not STORAGE_FILE.exists():
            return {}
        try:
            return json.loads(STORAGE_FILE.read_text())
        except Exception:
            return {}

    def _save(self):
        STORAGE_FILE.write_text(json.dumps(self.last_known, indent=2))

    def _fetch_deals(self):
        url = f"{BITRIX_WEBHOOK}/crm.deal.list.json"
        params = {
            "select[0]": "ID",
            "select[1]": "STAGE_ID",
            "order[ID]": "desc",
            "start": 0
        }
        r = requests.get(url, params=params)
        r.raise_for_status()
        return r.json().get("result", [])

    def run(self):
        print("[poll] Старт проверки сделок...")
        deals = self._fetch_deals()
        for deal in deals:
            deal_id = str(deal["ID"])
            stage = deal["STAGE_ID"]

            prev = self.last_known.get(deal_id)
            if stage == self.stage_id_done and prev != stage:
                print(f"✅ Обнаружен переход вручную! Сделка {deal_id} завершена.")
                notify_deal_complete(deal_id)  # 🔔 Отправка в Telegram

            self.last_known[deal_id] = stage

        self._save()


if __name__ == "__main__":
    DealWatcher().run()