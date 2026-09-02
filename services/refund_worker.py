import asyncio
import aiohttp
import aiosqlite
from database.db import DB_FILE
from services.support_bot import automate_missing_items

async def check_tracker_delivery(session: aiohttp.ClientSession, tracking_url: str) -> bool:
    """Fetches the Woolix eat-tracker link and checks if status is delivered."""
    try:
        async with session.get(tracking_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                html = await resp.text()
                html_lower = html.lower()
                # Check for delivered indicators in tracker payload/HTML
                if "delivered" in html_lower or "order completed" in html_lower or "enjoy your meal" in html_lower:
                    return True
    except Exception as e:
        print(f"[Tracker Poll Error for {tracking_url}]: {e}")
    return False

async def run_refund_worker(bot):
    """Background loop that polls tracking links every 5 minutes."""
    print("✅ Refund tracker worker started (5-minute intervals).")
    
    while True:
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute(
                    "SELECT job_id, discord_id, tracking_url, email, password FROM pending_refunds WHERE status = 'tracking'"
                ) as cur:
                    active_orders = await cur.fetchall()

            if active_orders:
                print(f"[Refund Worker] Checking {len(active_orders)} active orders for delivery...")
                async with aiohttp.ClientSession() as session:
                    for job_id, discord_id, tracking_url, email, password in active_orders:
                        # Skip if tracking URL is missing or generic
                        if not tracking_url or "eat-tracker.com" not in tracking_url:
                            continue

                        is_delivered = await check_tracker_delivery(session, tracking_url)
                        if is_delivered:
                            print(f"📦 Order {job_id} delivered on eat-tracker! Launching refund flow...")
                            
                            # Mark as processing
                            async with aiosqlite.connect(DB_FILE) as db:
                                await db.execute("UPDATE pending_refunds SET status = 'processing' WHERE job_id = ?", (job_id,))
                                await db.commit()

                            try:
                                await automate_missing_items(email, password)
                                async with aiosqlite.connect(DB_FILE) as db:
                                    await db.execute("UPDATE pending_refunds SET status = 'refunded' WHERE job_id = ?", (job_id,))
                                    await db.commit()
                                print(f"✅ Order {job_id} successfully refunded.")
                            except Exception as refund_err:
                                print(f"❌ Order {job_id} refund execution error: {refund_err}")
                                async with aiosqlite.connect(DB_FILE) as db:
                                    await db.execute("UPDATE pending_refunds SET status = 'failed' WHERE job_id = ?", (job_id,))
                                    await db.commit()

        except Exception as loop_err:
            print(f"[Refund Worker Exception]: {loop_err}")

        # Sleep 5 minutes (300 seconds)
        await asyncio.sleep(300)