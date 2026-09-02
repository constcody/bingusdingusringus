import aiohttp
from config.settings import settings

async def send_order_success_webhook(user_id: str, store_name: str, total_cents: int, tracking_url: str, email: str, password: str):
    if not settings.DISCORD_WEBHOOK_URL:
        return

    payload = {
        "content": f"<@{user_id}>",
        "embeds": [
            {
                "title": f"🎉 Successful Checkout — {store_name}",
                "color": 3066993,  # Green
                "fields": [
                    {"name": "💰 Total Charged", "value": f"${total_cents / 100:.2f}", "inline": True},
                    {"name": "🔗 Tracking Link", "value": f"[View Live Tracking]({tracking_url})", "inline": False},
                    {"name": "📧 Account Email", "value": f"`{email}`", "inline": True},
                    {"name": "🔑 Account Password", "value": f"`{password}`", "inline": True}
                ],
                "footer": {"text": "Red App Bot • Automated Checkout"}
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(settings.DISCORD_WEBHOOK_URL, json=payload) as resp:
            if resp.status not in [200, 204]:
                print(f"[Webhook Error]: Failed to send alert, status {resp.status}")