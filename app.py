from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import traceback

app = FastAPI()

@app.post("/webhook/unsafe_log")
async def unsafe_log(request: Request):
    try:
        raw = await request.body()
        headers = dict(request.headers)
        print("\n🔍 [UNSAFE_LOG] Raw body:", raw.decode(errors="ignore"))
        print("📩 Headers:", headers)
        return {"status": "ok", "length": len(raw)}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})