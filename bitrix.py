import os
import requests
from typing import Optional

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")

class BitrixClient:
    def __init__(self):
        if not BITRIX_WEBHOOK:
            raise ValueError("BITRIX_WEBHOOK not set")
        self.webhook = BITRIX_WEBHOOK

    def upload_file_to_folder(self, folder_id: int, filename: str, content: bytes) -> Optional[int]:
        files = {"file": (filename, content)}
        response = requests.post(f"{self.webhook}/disk.folder.uploadfile", data={"id": folder_id}, files=files)
        json_data = response.json()
        if "result" in json_data:
            return int(json_data["result"]["ID"])
        return None

    def attach_file_to_deal(self, deal_id: int, field_code: str, file_id: int) -> bool:
        response = requests.post(f"{self.webhook}/crm.deal.update", data={
            "id": deal_id,
            f"fields[{field_code}]": file_id
        })
        return response.json().get("result", False)