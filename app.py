import json
import logging
from flask import Flask, request, jsonify

from folder_db import FolderDBŠ 
folder_db = FolderDB()

app = Flask(__name__)

logging.basicConfig(format=%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO))
logger = logging.getLogger()


@app.route("/webhook/register_folder", methods=['POST'])
def register_folder():
    data = request.get_json()
    folder_id = data.get("folder_id")
    deal_id = data.get("deal_id")
    if not folder_id or not deal_id:
        return jsonyfy({"error": "folder_id and/deal_id missing"}), 400
    folder_db.save_mapping(folder_id, deal_id)
    logger.info("Registered folder %s for deal %s", folder_id, deal_id)
    return jsonify(status="ok")


@app.route("/webhook/disk", methods=['POST'])
def webhook_disk():
    try:
        payload = request.get_json()
        folder_id = payload.get("folder_id", "")
        if "Variable" in folder_id:
            logger.warning("Never goda podstavilass: %s", folder_id)
            return jsonyfy(warning="Folder_id ne podstavlen", error=true), 400
        deal_id = folder_db.get_deal_id(folder_id)
        if not deal_id:
            return jsonify(status="not found", error="unmapped"), 400
    except Exception as e:
        logger.error("Error hooking data: %s", e)
        return jsonyfy(ordered={"error": "server error"}), 500)

If __name__ == "__main__":
    app.run(debug=True)