# 📸 PostingFotoTG

**Назначение:** сервис для автоматической публикации фотографий в Telegram.

**Автор:** [@maslovmaksim92](https://github.com/maslovmaksim92)  
**Репозиторий:** [PostingFotoTG](https://github.com/maslovmaksim92/PostingFotoTG)

---

## 🚀 Возможности

- 📂 Чтение фото из папки / URL / внешнего источника
- 🤖 Отправка фото в Telegram-канал / группу
- 🕒 Планирование публикаций (cron, отложенные посты)
- 🧠 Интеграция с GPT / генерация описания к фото (по желанию)
- 📝 Логирование отправок и ошибок

---

## 🧱 Архитектура

Проект построен по принципам:
- **Clean Architecture**: чёткое разделение слоёв
- **Single Responsibility**: каждый модуль отвечает за своё
- **Асинхронность**: используется `asyncio`, `httpx`, `aiogram`

---

## 📁 Структура проекта

```
PostingFotoTG/
├── app.py                 # Точка входа, FastAPI-приложение
├── requirements.txt       # Зависимости
├── core/                  # Telegram логика, утилиты
├── api/                   # Роуты и бизнес-логика API
├── models/                # Pydantic схемы
├── docs/                  # (по желанию) спецификация OpenAPI
└── README.md
```

---

## 📦 Используемые технологии

- `FastAPI` + `uvicorn`
- `Telegram Bot API`
- `httpx`, `asyncio`
- `python-dotenv`
- `pydantic`
- `loguru`

---

## 🔐 Переменные окружения

Пример `.env`:
```env
TG_BOT_TOKEN=xxx:yyyyyyy
TG_CHAT_ID=-1001234567890
PHOTO_FOLDER=./images
```

---

## ⚙️ Запуск локально

```bash
git clone https://github.com/maslovmaksim92/PostingFotoTG.git
cd PostingFotoTG
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

---

## 📬 Пример отправки через API

```bash
curl -X POST http://localhost:8000/send-photo \
     -H "Content-Type: application/json" \
     -d '{"filename": "cat.jpg", "caption": "Милый котик!"}'
```

---

## 🧪 Тесты (опционально)

Пока не добавлены. Планируется использовать:
- `pytest`
- `pytest-httpx`
- `pytest-asyncio`

---

## 📌 TODO

- [ ] Вынести конфиг в pydantic-settings
- [ ] Dockerfile + GitHub Actions CI
- [ ] Планировщик публикаций по расписанию
- [ ] Хранилище логов (SQLite / Supabase)

---

## 📎 Полезные ссылки

- [@maslovmaksim92 GitHub](https://github.com/maslovmaksim92)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Telegram Bot API](https://core.telegram.org/bots/api)