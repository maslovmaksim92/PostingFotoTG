# 🚀 PostingFotoTG

**Автоматическая отправка фотоотчётов об уборке подъездов**

📦 Bitrix24 → GPT → Telegram

---

## 🔧 Как работает

1. В Bitrix24 сделка переходит в стадию **"Уборка завершена"**
2. Bitrix отправляет вебхук:
   ```json
   POST /webhook/register_folder
   {
     "deal_id": 12345,
     "folder_id": 199058
   }
   ```
3. FastAPI-приложение:
   - Загружает фото из Bitrix (по folder_id)
   - Генерирует текст (GPT)
   - Отправляет сообщение и медиа в Telegram

---

## 📡 Маршруты API

| Метод | Путь                      | Назначение            |
|-------|---------------------------|------------------------|
| GET   | `/`                       | Healthcheck            |
| POST  | `/webhook/register_folder` | 📥 Основной webhook    |
| POST  | `/webhook/debug_log`     | 🐞 Логгирование тела    |
| POST  | `/webhook/test`          | 🔁 Тестовый маршрут     |

---

## 🤖 GPT-генерация (OpenAI)

| Параметр     | Значение          |
|--------------|-------------------|
| Модель       | gpt-3.5-turbo     |
| Температура  | 0.9               |
| Prompt       | Вдохновляющий текст уборки |
| Fallback     | "Уборка завершена. Спасибо за чистоту 🧹" |

---

## 🖼️ Telegram

- `sendMediaGroup` для фото
- `.mp4` отправляется отдельно
- Поддержка Markdown в подписи

---

## 🛠 Используемые поля Bitrix

| Назначение      | UF_ код поля            |
|-----------------|-------------------------|
| Папка файлов     | `UF_CRM_1686038818`     |
| Фото            | `UF_CRM_1740994275251`  |
| Адрес           | `UF_CRM166956159956`    |
| Даты и типы     | `UF_CRM1741590925181`, `UF_CRM174159176502` |

---

## 🌍 Пример curl

```bash
curl -X POST https://postingfototg.onrender.com/webhook/register_folder \
  -H "Content-Type: application/json" \
  -d '{"deal_id": 11720, "folder_id": 199058}'
```

---

## 🔐 .env (пример)

```env
TG_GITHUB_BOT=xxx
TG_CHAT_ID=xxx
OPENAI_API_KEY=sk-xxx
BITRIX_WEBHOOK=https://.../rest/1/...
FILE_FIELD_ID=UF_CRM_...
```

---

## 🧠 Стек

- `FastAPI`, `httpx`, `pydantic`
- `OpenAI GPT`, `loguru`, `requests`
- `Telegram Bot API`, `Markdown`
- `Render`, `GitHub Actions`

---

## 👨‍💻 Автор

Разработано совместно с GPT 🤖
> Специально для компании **"Ваш Дом"**, г. Калуга