import time
import aiohttp
from config.settings import settings

NOWPAYMENTS_API_URL = "https://api.nowpayments.io/v1"

async def create_invoice(user_id: str, amount_usd: float):
    """Creates a NOWPayments invoice."""
    headers = {
        "x-api-key": settings.NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "price_amount": amount_usd,
        "price_currency": "usd",
        "pay_currency": "sol",
        "order_id": f"deposit_{user_id}_{int(time.time())}",
        "order_description": f"Deposit ${amount_usd:.2f} for user {user_id}"
    }

    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(f"{NOWPAYMENTS_API_URL}/invoice", json=payload, headers=headers) as resp:
            data = await resp.json()
            if resp.status in [200, 201]:
                return data, 200
            return data, resp.status