from fastapi import FastAPI
from routers import webhook

app = FastAPI()

@app.get("/")
async def health():
    return {"status": "ok"}

app.include_router(webhook.router)