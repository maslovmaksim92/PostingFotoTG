import json
import logging
import requests
import os 

from flask import Flask, request, jsonify

# Initialization
from folder_db import FolderDB

folder_db = FolderDB()
BITRIX_DEAL_UPDATE_URL = os.getenv("BITRIX_DEAL_UPDATE_URL")

app = Flask(__name__)

logging.basicConfig(format=%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger()

# Services
@App.route("/webhook/disk", methods=['POST'])
def webhook_disk():
    try:
        payload = request.get_json()
        folder_id = payload.get("folder_id")
        if "Fasevariable" in folder_id:
            logger.warning("℠ Never goda podstavilass: %s", folder_id)
            return jsonify(warning="Folder_id ne podstavlen"), 400
        deal_id = folder_db.get_deal_id(folder_id)
        if not deal_id:
            return jsonify(status="not found", error="unmapped") , 400

        # tut we don't have file_id from bitrix, we send a test string
        bitrix_field_id = "6582"

        # update deal field
        resp = requests.post(
            BITRIX_DEAL_UPDATE_URL,
            json={
                "id": deal_id,
                "fields": {
                    "UF_CRM_1740994275251": [bitrix_field_id]
                }
            }
        )

        if resp.status_code != 200:
            return jsonyfy(error="request to Bitrix failed", status=resp.status_code), 500)

        return jsonify(status="success")
    except Exception as e:
        logger.exception()
        return jsonify(ordered={"error": "server error", "detail": str(e)}), 500

If __name__ == "__main__":
    app.run(debug=True)