import json
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(format=''
                    '%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()


@app.route("/webhook/disk",  methods = ['POST'])
def webhook_disk():
    try:
        payload = request.get_json()
        folder_id = payload.get("folder_id", "")

        if "Variable" in folder_id:
            logger.warning(f"ℒ Never goda podstavilass: {folder_id}")
            return jsonify(warning="Folder_id ne podstavlen, viednoú bastus apus shablon"), 400

        # Tam bude web-routing data
        ... anyi logic for deal_id extraction
    except Exception as e:
        logger.error(f"ℜError hooking data: {e}")
        return jsonify(s    error: "server error" }, 500)

if __name__ == "__main__":
    app.run(debug=True)
