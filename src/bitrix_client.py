import httpx
import os

BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")


async def get_deal_files(deal_id: str):
    async with httpx.AsyncClient() as client:
        url = f"{BITRIX_WEBHOOK}/crm.deal.get"
        resp = await client.get(url, params={"ID": deal_id})
        resp.raise_for_status()

        data = resp.json()
        deal = data.get("result", {})
        print(f"👉 Сделка #{deal_id} получена")

        return deal