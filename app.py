import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

WEBHOOK_BASE = "https://vas-dom.bitrix24.ru/rest/1/gq2ixv9nypiimwi9"
FOLDER_CHILDREN_METHOD = f"{WEBHOOK_BASE}/disk.folder.getchildren.json"
DEAL_UPDATE_METHOD = f"{WEBHOOK_BASE}/crm.deal.update.json"

FIELD_CODE = "UF_CRM_1740994275251"  # поле "Файл" множественное

@app.route("/attach_files", methods=["GET"])
def attach_files():
    deal_id = request.args.get("deal_id")
    folder_id = request.args.get("folder_id")

    if not deal_id or not folder_id:
        return jsonify({"error": "[❌] Не передан deal_id или folder_id"}), 400

    try:
        resp = requests.post(FOLDER_CHILDREN_METHOD, json={"id": folder_id})
        data = resp.json()
    except Exception as e:
        return jsonify({"error": f"Ошибка запроса к Bitrix: {str(e)}"}), 500

    result = data.get("result", [])
    if not result:
        return jsonify({"error": "[❌] Папка пуста или недоступна"}), 400

    files_for_update = {}
    index = 0

    for file_info in result:
        url = file_info.get("DOWNLOAD_URL")
        name = file_info.get("NAME", f"file{index}.bin")

        if not url:
            continue

        try:
            file_resp = requests.get(url)
            file_resp.raise_for_status()
        except Exception as e:
            print(f"[⚠️] Ошибка скачивания {name}: {e}")
            continue

        key = f"fields[{FIELD_CODE}][{index}][fileData][]"
        files_for_update[key] = (name, file_resp.content, "application/octet-stream")
        index += 1

    if not files_for_update:
        return jsonify({"error": "[❌] Ни один файл не был скачан"}), 400

    try:
        update_resp = requests.post(
            DEAL_UPDATE_METHOD,
            data={"id": deal_id},
            files=files_for_update
        )
        update_data = update_resp.json()
    except Exception as e:
        return jsonify({"error": f"Ошибка обновления сделки: {str(e)}"}), 500

    if update_data.get("result") is True:
        return jsonify({"status": "OK", "message": f"[✅] Файлы прикреплены к сделке #{deal_id}"})
    else:
        return jsonify({"error": "[❌] Bitrix не принял файлы", "response": update_data}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
