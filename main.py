import os
import asyncio
from config.settings import settings
from database.db import init_db
from bot.client import bot
from services.zelle_worker import check_zelle_emails
from services.refund_worker import run_refund_worker
from services.daily_worker import run_daily_volume_worker

def init_cards_file():
    """Initializes cards.txt from environment variable on Railway if available."""
    data_dir = "/app/data" if os.path.exists("/app/data") else "."
    cards_path = os.path.join(data_dir, "cards.txt")
    cards_env = os.getenv("CARDS_TXT")
    if cards_env and not os.path.exists(cards_path):
        with open(cards_path, "w") as f:
            f.write(cards_env.strip() + "\n")
        print("  cards.txt generated from environment variable.")

async def run_bot():
    if not settings.DISCORD_BOT_TOKEN:
        print("[Error] DISCORD_BOT_TOKEN missing in .env")
        return
    await bot.start(settings.DISCORD_BOT_TOKEN)

async def main():
    init_cards_file()
    await init_db()
    print("  Database initialized.")
    await asyncio.gather(
        run_bot(),
        check_zelle_emails(bot),
        run_refund_worker(bot),
        run_daily_volume_worker(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())