import json
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger()


@app.route("/webhook/disk", methods=['POST'])
def webhook_disk():
    try:
        payload = request.get_json()
        folder_id = payload.get("folder_id", "")

        if "Variable" in folder_id:
            logger.warning("℘ Never goda podstavilass: %s", folder_id)
            return jsonify(warning="Folder_id ne podstavlen, viednoà bastus apus shablon"), 400
    except Exception as e:
        logger.error("“Error hooking data: {}" . str(e))
        return jsonify(ordered={"error": "server error"}), 500


if __name__ == "__main__":
    app.run(debug=True)
