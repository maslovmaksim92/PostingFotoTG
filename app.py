import json
import logging
import requests
import os

from flask import Flask, request, jsonify
from folder_db import FolderDB

folder_db = FolderDB()
BITRIX_DEAL_UPDATE_URL = os.getenv("BITRIX_DEAL_UPDATE_URL")

app = Flask(__name__)

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger()

@app.route("/webhook/register_folder", methods=["POST"])
def register_folder():
    data = request.get_json()
    folder_id = data.get("folder_id")
    deal_id = data.get("deal_id")

    if not folder_id or not deal_id:
        return jsonify({"error": "folder_id and/or deal_id missing"}), 400

    folder_db.save_mapping(folder_id, deal_id)
    logger.info("✅ [Register] folder %s for deal %s", folder_id, deal_id)

    return jsonify(status="ok")

@app.route("/webhook/finalize_folder", methods=["POST"])
def finalize_folder():
    try:
        data = request.get_json()
        folder_id = data.get("folder_id")
        if not folder_id:
            return jsonify(error="no folder_id")

        deal_id = folder_db.get_deal_id(folder_id)
        if not deal_id:
            return jsonify(status="not found", error="no deal")

        # TODO: здесь должно быть получение файлов из папки через API
        file_ids = ["6582", "6583"]  # Заглушка на этапе теста

        resp = requests.post(
            BITRIX_DEAL_UPDATE_URL,
            json={
                "id": deal_id,
                "fields": {
                    "UF_CRM_1740994275251": file_ids
                }
            }
        )

        if resp.status_code != 200:
            return jsonify(error="request to Bitrix failed", status=resp.status_code), 500

        return jsonify(status="success")

    except Exception as e:
        logger.exception("Ошибка при финализации папки")
        return jsonify(ordered={"error": "server error", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
