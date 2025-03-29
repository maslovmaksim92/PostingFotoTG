from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os

# Загрузка переменных из .env
load_dotenv()

app = Flask(__name__)

@app.route('/upload_photos', methods=['POST'])
def upload_photos():
    data = request.get_json()
    folder_id = data.get('folder_id')

    if not folder_id:
        return jsonify({"status": "error", "message": "folder_id отсутствует"}), 400

    return jsonify({"status": "ok", "folder_id": folder_id})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
