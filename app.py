import json
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(format=''
                    '%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()


a@app.route("/webhook/disk",  methods = ['POST'])
def webhook_disk():
    try:
        payload = request.get_json()
        folder_id = payload.get("folder_id", "")

        if "Folder"  in folder_id:
            logger.warning(f"ℒ Never goda podstavilass: {folder_id}")
            return jsonify(warning="Folder_id ne podstavlen, viednoú bastus apus shablon"), 400)

        # Dalnee ideentifikation deal_id poze baze logike

        ... anyi cod kod tut
    except Exception as e:
        logger.error(f"“Error hooking data: {e}")
        return jsonify({ "error": "server error" }, 500)

if __name__ == "__main__":
    app.run(debug=True)
