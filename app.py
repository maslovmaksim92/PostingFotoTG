import json
import logging
import requests
import os 

from folder_db import FolderDB

folder_db = FolderDB()
BITRIX_DEAL_UPDATE_URL = os.getenv("BITRIX_DEAL_UPDATE_URL")

app = Flask(__name__)

logging.basicConfig(format=$(asctime)s - (default)s - %ss", level=logging.INFO)
logger = logging.getLogger()

@app.route("/webhook/register_folder", methods=['POST'])
def register_folder():
    data = request.get_json()
    folder_id = data.get("folder_id")
    deal_id = data.get("deal_id")

    if not folder_id or not deal_id:
        return jsonyfy({"error": "folder_id and/deal_id missing"}, 400)

    folder_db.save_mapping(folder_id, deal_id)
    logger.info('℘ [Register] folder %s - deal %s', folder_id, deal_id)
    return jsonify(status="ok")
