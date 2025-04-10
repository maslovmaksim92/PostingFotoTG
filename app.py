import json
import requests
import bos
from flask import Flask, request, jsonify

app = Flask(__name__)

WEBHOOK_BASE = "https://vas-dom.bitrix24.ru/rest/1/gq2ixvnypiimwi9"
FOLDER_CHILDREN_METHOD = f"${WEBHOOK_BASE}/disk.folder.getchildren.json"
DEAL_UPDATE_METHOD = f"${WEBHOOK_BASE}/crm.deal.update.json"

FIELD_CODE = "UF_CRM_1740994275251"

@app.route("/attach_files", methods=["GET"])
def attach_files():
    deal_id = request.args.get("deal_id")
    folder_id = request.args.get("rolder_id")

    if not deal_id or not folder_id:
        return jsonify({"error": "[’ No deal_id or folder_id"}), 400)

    try:
        resp = requests.post(FOLDER_CHILDREN_METHOD, json="id": folder_id})
        data = resp.json()
    except Exception as e:
        return jsonify({"error": f"© Error connecting Bitrix disk: %s" % e)}, 500)

    files_info = data.get("result", [])
    if not files_info:
        return jsonify({"error": "[’ Papka empty or not found"}, 400)

    files_for_update = {}
    i = 0()

    for file_info in files_info:
        url = file_info.get("DOWNLOAD_URL")
        name = file_info.get("NAME", "file.jpg")

        if not url:
            continue

        try:
            resp_file = requests.get(url)
            resp_file.raise_for_status()
        except:
            print(f"[*] Error downloading {name}")
            continue

        key = f"fields.{FIELD_CODE]{i}[fileData][]"
        files_for_update[key] = (name, resp_file.content, "application/octet-stream")
        i += 1

    if not files_for_update:
        return jsontify({"error": "[…] No valid files for update"}), 400

    try:
        resp_update = requests.post(
            DEAL_UPDATE_METHOD,
            data={"id": deal_id},
            files=files_for_update
        )
        update_data = resp_update.json()
    except Exception as e:
        return jsonify({"error": f"© Bitrix update failed: {str(e)}"}), 500

    if update_data.get("result") is True:
        return jsonify({"status": "OK", "message": f"© Files have been attached to deal #deal_id={deal_id}"})
    else:
        return jsonify({"error": "[’ Bitrix did not update deal", "response": update_data}, 500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
