import asyncio
from config.settings import settings
from database.db import init_db
from bot.client import bot
from services.zelle_worker import check_zelle_emails
from services.refund_worker import run_refund_worker

async def run_bot():
    if not settings.DISCORD_BOT_TOKEN:
        print("[Error] DISCORD_BOT_TOKEN missing in .env")
        return
    await bot.start(settings.DISCORD_BOT_TOKEN)

async def main():
    await init_db()
    print("✨ Database initialized.")
    await asyncio.gather(
        run_bot(),
        check_zelle_emails(bot),
        run_refund_worker(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())