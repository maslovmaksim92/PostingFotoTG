from fastapi import FastAPI, HTTPException
from bitrix import BitrixClient
from pathlib import Path

app = FastAPI()

@app.post("/test-attach")
def test_attach():
    bitrix = BitrixClient()

    file_path = Path("image.png")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл image.png не найден")

    with file_path.open("rb") as f:
        content = f.read()

    # Загрузка файла в папку
    folder_id = 198874
    deal_id = 11720
    field_code = "UF_CRM_1744310845527"

    file_id = bitrix.upload_file_to_folder(folder_id, "image.png", content)
    if not file_id:
        raise HTTPException(status_code=400, detail="Ошибка загрузки файла в папку Bitrix")

    success = bitrix.attach_file_to_deal(deal_id, field_code, file_id)
    if not success:
        raise HTTPException(status_code=400, detail="Не удалось прикрепить файл к сделке")

    return {"status": "ok", "file_id": file_id}