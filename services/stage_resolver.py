import requests
import os

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")


class StageResolver:
    def __init__(self):
        self._stages = None

    def _fetch_stages(self):
        url = f"{BITRIX_WEBHOOK}/crm.status.list.json"
        response = requests.get(url)
        response.raise_for_status()
        result = response.json()
        self._stages = result.get("result", [])

    def get_stage_id_by_name(self, name: str) -> str | None:
        if self._stages is None:
            self._fetch_stages()

        for stage in self._stages:
            if stage.get("NAME") == name:
                return stage.get("STATUS_ID")

        return None


stage_resolver = StageResolver()