import pytest
from httpx import AsyncClient
from app import app
import os

@pytest.mark.asyncio
async def test_invalid_token():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/webhook/deal_update", json={
            "event": "ONCRMDEALUPDATE",
            "data": {"FIELDS": {"ID": "123", "STAGE_ID": "C8:FINISHED"}},
            "auth": {"application_token": "wrong-token"}
        })
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_wrong_stage(monkeypatch):
    monkeypatch.setenv("BITRIX_TG_WEBHOOK_ISHOD", "test-token")
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/webhook/deal_update", json={
            "event": "ONCRMDEALUPDATE",
            "data": {"FIELDS": {"ID": "124", "STAGE_ID": "C2:NEW"}},
            "auth": {"application_token": "test-token"}
        })
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"

@pytest.mark.asyncio
async def test_success_stage(monkeypatch):
    monkeypatch.setenv("BITRIX_TG_WEBHOOK_ISHOD", "test-token")
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/webhook/deal_update", json={
            "event": "ONCRMDEALUPDATE",
            "data": {"FIELDS": {"ID": "125", "STAGE_ID": "C8:FINISHED"}},
            "auth": {"application_token": "test-token"}
        })
    assert response.status_code == 200
    assert response.json()["status"] == "processed"