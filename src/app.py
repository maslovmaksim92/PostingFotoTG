from fastapi import FastAPI
from webhook import router as webhook_router

app = FastAPI()

app.include_router(webhook_router)


@app.get("/ping")
async def ping():
    return {"status": "ok"}