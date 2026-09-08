import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import discord
from database.db import get_daily_volume

DAILY_CHANNEL_ID = 1546910021701345421
TIMEZONE = ZoneInfo("America/New_York")  # EST/EDT

async def run_daily_volume_worker(bot):
    """Runs continuously and posts daily total volume every day at 8:00 PM EST."""
    print("  Daily volume worker started (Scheduled for 8:00 PM EST daily).")
    await bot.wait_until_ready()

    while not bot.is_closed():
        now = datetime.now(TIMEZONE)

        # Target today at 8:00 PM (20:00)
        target = now.replace(hour=20, minute=0, second=0, microsecond=0)

        # If 8:00 PM has already passed today, schedule for tomorrow 8:00 PM
        if now >= target:
            target = target.replace(day=target.day + 1)

        wait_seconds = (target - now).total_seconds()
        print(f"[Daily Worker] Sleeping for {int(wait_seconds)} seconds until 8:00 PM EST...")
        await asyncio.sleep(wait_seconds)

        # Send daily volume
        try:
            total_cents, order_count = await get_daily_volume()
            total_usd = total_cents / 100.0

            channel = bot.get_channel(DAILY_CHANNEL_ID)
            if channel is None:
                channel = await bot.fetch_channel(DAILY_CHANNEL_ID)

            if channel:
                date_str = datetime.now(TIMEZONE).strftime("%B %d, %Y")
                embed = discord.Embed(
                    title=f"📊 Daily Volume Summary — {date_str}",
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(
                    name="💰 Total Volume",
                    value=f"**${total_usd:,.2f}**",
                    inline=True
                )
                embed.add_field(
                    name="📦 Orders Placed",
                    value=f"**{order_count}**",
                    inline=True
                )
                if order_count > 0:
                    avg_ticket = total_usd / order_count
                    embed.add_field(
                        name="🏷️ Average Ticket",
                        value=f"${avg_ticket:.2f}",
                        inline=True
                    )
                embed.set_footer(text="Daily Volume Recap • 8:00 PM EST")

                await channel.send(embed=embed)
                print(f"[Daily Worker] Successfully sent 8:00 PM report: ${total_usd:.2f} across {order_count} orders.")
        except Exception as e:
            print(f"[Daily Worker Error]: {e}")

        # Small 60-second delay so it doesn't trigger repeatedly in the same second
        await asyncio.sleep(60)