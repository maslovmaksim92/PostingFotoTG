from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import traceback

app = FastAPI()

@app.post("/webhook/debug_log")
async def debug_log(request: Request):
    try:
        payload = await request.json()
        print("📩 [DEBUG_LOG] Payload from Bitrix:", payload)
        return {"status": "ok", "received": payload}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})