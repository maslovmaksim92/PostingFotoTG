from fastapi import FastAPI, Request
from loguru import logger

app = FastAPI()


@app.post("/webhook/unsafe_log")
async def unsafe_log(request: Request):
    body = await request.json()
    headers = dict(request.headers)

    logger.warning("[UNSAFE_LOG] Raw body: {}", body)
    logger.warning("📩 Headers: {}", headers)

    return {"status": "ok", "length": len(str(body))}