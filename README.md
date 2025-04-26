## 📤 Загрузка файлов в Bitrix

Для прямой загрузки файлов используется функция `upload_file_to_bitrix` из модуля `bitrix_upload.py`.

Пример вызова:
```python
from bitrix_upload import upload_file_to_bitrix
upload_file_to_bitrix("/tmp/photo.jpg", folder_id=123456)
```

Логи записываются в `logs/uploader.log`.
