from fastapi import FastAPI
from loguru import logger
from senders.telegram import send_cleaning_report

app = FastAPI()

@app.get("/")
def health_check():
    logger.info("Health check passed")
    return {"status": "ok"}

@app.get("/test/send-cleaning/{deal_id}")
@app.post("/test/send-cleaning/{deal_id}")
async def test_cleaning(deal_id: int):
    await send_cleaning_report(deal_id)
    return {"status": "sent", "deal_id": deal_id}