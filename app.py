from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import requests
import traceback
import time

app = FastAPI()

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")

FIELD_FILE = "UF_CRM_1740994275251"
FIELD_HTML = "UF_CRM_PHOTO_HTML_BLOCK"

class AttachRequest(BaseModel):
    deal_id: int
    folder_id: int

class BitrixClient:
    def __init__(self):
        if not BITRIX_WEBHOOK:
            raise ValueError("BITRIX_WEBHOOK not set")
        self.webhook = BITRIX_WEBHOOK

    def get_files_from_folder(self, folder_id: int):
        resp = requests.get(f"{self.webhook}/disk.folder.getchildren", params={"id": folder_id})
        return resp.json().get("result", [])

    def update_deal_fields(self, deal_id: int, fields: dict) -> bool:
        payload = {"id": deal_id, "fields": fields}
        resp = requests.post(f"{self.webhook}/crm.deal.update", json=payload)
        return resp.json().get("result", False)

    def get_deal_fields(self, deal_id: int) -> dict:
        resp = requests.get(f"{self.webhook}/crm.deal.get", params={"id": deal_id})
        return resp.json().get("result", {})

    def create_html_field(self) -> dict:
        payload = {
            "FIELD_NAME": FIELD_HTML,
            "EDIT_FORM_LABEL": {"ru": "ФОТО ГАЛЕРЕЯ HTML"},
            "USER_TYPE_ID": "string",
            "MULTIPLE": "N",
            "SHOW_IN_LIST": "Y",
            "EDIT_IN_LIST": "Y",
            "IS_SEARCHABLE": "N"
        }
        resp = requests.post(f"{self.webhook}/crm.deal.userfield.add", json={"fields": payload})
        return resp.json()

@app.post("/attach-folder")
def attach_folder(req: AttachRequest):
    try:
        bitrix = BitrixClient()
        files = bitrix.get_files_from_folder(req.folder_id)
        file_ids = []
        html_blocks = []

        for f in files:
            fid = f.get("ID")
            url = f.get("DOWNLOAD_URL")
            if fid and url:
                file_ids.append(fid)
                html_blocks.append(f'<img src="{url}" style="max-width:100%;margin-bottom:10px;"/>')

        bitrix.update_deal_fields(req.deal_id, {
            FIELD_FILE: file_ids,
            FIELD_HTML: "\n".join(html_blocks)
        })

        return {"status": "ok", "files_attached": len(file_ids)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug-deal-files")
def debug_deal_files():
    try:
        bitrix = BitrixClient()
        data = bitrix.get_deal_fields(11720)
        return {
            "file_field": data.get(FIELD_FILE),
            "html_block": data.get(FIELD_HTML)
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create-html-field")
def create_html_field():
    try:
        bitrix = BitrixClient()
        result = bitrix.create_html_field()
        return {"status": "created", "bitrix_response": result}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))