from fastapi import FastAPI
from webhook import router as webhook_router
from debug.files_summary import router as debug_router

app = FastAPI()

app.include_router(webhook_router)
app.include_router(debug_router)  # Добавлен debug endpoint
