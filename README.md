# PostingFotoTG (v2.0)

## 🚀 Что делает проект:
- Получает файлы из папки Bitrix по `folder_id`
- Загружает файлы в сделку Bitrix24 (прикрепляет к полю)
- Отправляет фото в Telegram через `sendMediaGroup`
- Генерирует подпись к фото через GPT или fallback текст

---

## 📂 Финальная структура проекта:

| Файл                | Назначение                                  |
|---------------------|--------------------------------------------|
| `app.py`            | FastAPI точка входа                        |
| `webhook.py`        | Обработка webhook событий Bitrix           |
| `services.py`       | Логика загрузки файлов и отправки отчёта   |
| `bitrix.py`         | Работа с Bitrix API (сделки, файлы)         |
| `telegram.py`       | Отправка фото/видео в Telegram             |
| `gpt.py`            | Генерация подписей через OpenAI GPT        |
| `config.py`         | Настройки проекта                         |
| `utils/formatting.py`| Форматирование дат, fallback текст         |
| `utils/prompts.py`  | Промпты для генерации GPT                 |
| `requirements.txt`  | Зависимости проекта                       |
| `tests/`            | Тесты проекта                             |

---

## 🛠 Технологии:
- **FastAPI** + **Uvicorn**
- **Bitrix24 REST API**
- **Telegram Bot API**
- **OpenAI GPT-3.5/4**
- **httpx** / **aiohttp** / **requests**

---

## 📬 Основные роуты:

| Метод | URL                   | Описание                         |
|-------|------------------------|----------------------------------|
| POST  | `/webhook/register_folder` | Регистрация папки файлов по сделке |
| POST  | `/webhook/deal_update`     | Обработка изменения сделки (для Bitrix)|

---

## 📦 Требования:

- Python 3.11+
- Файл `.env`:
```env
BITRIX_WEBHOOK=https://yourdomain.bitrix24.ru/rest/1/...
TG_GITHUB_BOT=your-bot-token
TG_CHAT_ID=your-chat-id
OPENAI_API_KEY=your-openai-key
FILE_FIELD_ID=UF_CRM_1740994275251
FOLDER_FIELD_ID=UF_CRM_1743273170850
```

---

✅ Проект готов к деплою и продакшен-использованию внутри компании 🚀