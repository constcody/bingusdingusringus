from fastapi import FastAPI, Request
from database.db import adjust_balance
from bot.client import bot

app = FastAPI(title="DoorDash Bot Webhooks")

@app.post("/webhook/nowpayments")
async def nowpayments_webhook(request: Request):
    payload = await request.json()
    payment_status = payload.get("payment_status")

    # NOWPayments sends 'finished' or 'confirmed' when funds clear
    if payment_status in ["finished", "confirmed"]:
        order_id = payload.get("order_id", "")
        # Format: deposit_{discord_id}_{timestamp}
        parts = order_id.split("_")
        if len(parts) >= 2:
            discord_id = parts[1]
            amount_usd = float(payload.get("actually_paid", payload.get("price_amount", 0)))
            amount_cents = int(round(amount_usd * 100))

            if discord_id and amount_cents > 0:
                await adjust_balance(discord_id, amount_cents)
                print(f"[NOWPayments] Credited ${amount_usd:.2f} to user {discord_id}")

                # Send confirmation DM
                try:
                    user = await bot.fetch_user(int(discord_id))
                    if user:
                        await user.send(
                            f"✅ **Deposit Confirmed!**\n**${amount_usd:.2f}** has been automatically added to your balance."
                        )
                except Exception as e:
                    print(f"[NOWPayments DM Error]: {e}")

    return {"status": "ok"}