import httpx
from loguru import logger
from os import getenv


class Bitrix:
    def __init__(self) -> None:
        self.webhook = getenv("BITRIX_WEBHOOK")
        assert self.webhook, "BITRIX_WEBHOOK is not set"

    async def call(self, method: str, params: dict) -> dict:
        url = f"{self.webhook}/{method}"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=params)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Bitrix call failed: {e.response.text}")
            raise
        return response.json()