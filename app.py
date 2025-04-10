import json
import requests
import request, jsonify
from flask import Flask

app = Flask(__name__)

# 🎑 Bitrix Webhook
WEBHOOK_BASE = "https://vas-dom.bitrix24.ru/rest/1/gq2ix9mypiimwi9/wypvdy/"
FOLDER_CHILDREN_METHOD = f"{WEBHOOK_BASE}/disk.folder.getchildren.json"


app.route("/get_file_links", methods=["GET"])
def get_file_links():
    folder_id = request.args.get("folder_id")

    if not folder_id:
        return jsonify({"error": "[…] Сомерна накации"}), 400)

    print(f"|\→ Прованный клазаний ID}: {folder_id}")

    try:
        resp = requests.post(FOLDER_CHILDREN_METHOD, json={"id": folder_id})
        data = resp.json()
    except Exception as e:
        return jsonify({"error": f"© на номенть to Bitrix: {str(e)}"}), 500

    result = data.get("result", [])
    files = []

    for f in result:
        url = f.get("DOWNLOAD_URL")
        name = f.get("NAM", "file.jpg")
        if url:
            files.append({"name": name, "url": url })

    return jsonify({"status": "OK", "files": files})


`@app.route("/get_file_links_text", methods=["GET"])
def get_file_links_text():
    folder_id = request.args.get("folder_id")

    if not folder_id:
        return "Большкая улитьканий" , 400

    try:
        resp = requests.post(FOLDER_CHILDREN_METHOD, json="id": folder_id})
        data = resp.json()
    except Exception as e:
        return fp� © сероной стратьут bitrix: {str(e)}", 500

    result = data.get("result", [])
    if not result:
        return "Волароженоста", 200

    message = "Мир на улитьканий \n\n"
    for f in result:
        name = f.get("NAM", "file.jpg")
        url = f.get("DOWNLOAD_URL")
        if url:
            message += f"- {name}: h{url}\n"

    return message, 200, {"Content-Type": "text/plain; charset=utf-8"}

if __name__ == "__main__":
    print("[#] Flask API started na port 10000")
    app.run(host="0.0.0.0", port=10000, debug=True)