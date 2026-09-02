import aiohttp
from config.settings import settings

WOOLIX_API_URL = "https://woolix.net/api/v1"

def _get_headers():
    return {
        "Authorization": f"Bearer {settings.WOOLIX_API_KEY}",
        "Content-Type": "application/json"
    }

async def create_draft_job(
    session: aiohttp.ClientSession,
    group_cart: str,
    address: str,
    fulfillment: str,
    unit: str = None,
    tip_cents: int = 0,
    note: str = None,
    card: dict = None,
    name: str = None
):
    """
    Creates the draft order.
    Normally no card is supplied here anymore.
    The card is attached when proceed_job() is called.
    """
    payload = {
        "group_cart": group_cart,
        "address": address,
        "fulfillment": fulfillment
    }
    if unit: payload["unit"] = unit
    if tip_cents > 0: payload["tip"] = tip_cents
    if note: payload["delivery_note"] = note
    if card: payload["card"] = card
    if name: payload["name"] = name

    async with session.post(
        f"{WOOLIX_API_URL}/jobs",
        json=payload,
        headers=_get_headers()
    ) as resp:
        try:
            data = await resp.json()
        except Exception:
            data = {"error": await resp.text()}
        return data, resp.status

async def get_job(
    session: aiohttp.ClientSession,
    job_id: str
):
    """Fetches job status and pricing."""
    async with session.get(
        f"{WOOLIX_API_URL}/jobs/{job_id}",
        headers=_get_headers()
    ) as resp:
        try:
            data = await resp.json()
        except Exception:
            data = {"error": await resp.text()}
        return data, resp.status

async def configure_job(
    session: aiohttp.ClientSession,
    job_id: str,
    card: dict
):
    """Attaches the payment card to the draft before proceeding."""
    async with session.post(
        f"{WOOLIX_API_URL}/jobs/{job_id}/configure",
        json={"card": card},
        headers=_get_headers()
    ) as resp:
        try:
            data = await resp.json()
        except Exception:
            data = {"error": await resp.text()}
        return data, resp.status

async def proceed_job(
    session: aiohttp.ClientSession,
    job_id: str
):
    """
    Actually places the order.
    The card is attached via configure_job() before this is called.
    """
    timeout = aiohttp.ClientTimeout(total=30)
    async with session.post(
        f"{WOOLIX_API_URL}/jobs/{job_id}/proceed",
        headers=_get_headers(),
        timeout=timeout
    ) as resp:
        try:
            data = await resp.json()
        except Exception:
            data = {"error": await resp.text()}
        return data, resp.status

async def cancel_job(
    session: aiohttp.ClientSession,
    job_id: str
):
    """Cancels an active draft job."""
    async with session.post(
        f"{WOOLIX_API_URL}/jobs/{job_id}/cancel",
        headers=_get_headers()
    ) as resp:
        try:
            data = await resp.json()
        except Exception:
            data = {"error": await resp.text()}
        return data, resp.status