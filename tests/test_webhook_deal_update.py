import pytest
from httpx import AsyncClient
from app import app
import os

@pytest.mark.asyncio
async def test_deal_update_cleaning_done(monkeypatch):
    monkeypatch.setenv("BITRIX_TG_WEBHOOK_ISHOD", "test-token")

    # Подменим stage_resolver внутри webhook
    from routers import webhook
    webhook.stage_resolver.get_stage_id_by_name = lambda name: "C8:FINISHED"

    async with AsyncClient(app=app, base_url="http://test") as ac:
        data = {
            "auth[application_token]": "test-token",
            "data": '{"FIELDS": {"ID": "999", "STAGE_ID": "C8:FINISHED"}}'
        }
        response = await ac.post("/webhook/deal_update", data=data)

    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert response.json()["deal_id"] == "999"