from fastapi import FastAPI, Request
from database.db import adjust_balance

app = FastAPI(title="DoorDash Bot Webhooks")

@app.post("/webhook/oxapay")
async def oxapay_webhook(request: Request):
    payload = await request.json()
    status = payload.get("status")

    if status == "Paid":
        order_id = payload.get("order_id", "")
        # Format: {discord_id}_{amount_cents}
        parts = order_id.split("_")
        if len(parts) >= 2:
            discord_id = parts[0]
            amount_usd = float(payload.get("amount", 0))
            amount_cents = int(amount_usd * 100)

            if discord_id and amount_cents > 0:
                await adjust_balance(discord_id, amount_cents)
                print(f"[OxaPay Webhook]: Credited ${amount_usd:.2f} to user {discord_id}")

    return {"status": "ok"}