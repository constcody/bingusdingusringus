import os
import aiosqlite

DATA_DIR = "/app/data" if os.path.exists("/app/data") else "."
DB_FILE = os.path.join(DATA_DIR, "bot.db")

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                discord_id TEXT PRIMARY KEY,
                balance_cents INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_deposits (
                ref_code TEXT PRIMARY KEY,
                discord_id TEXT NOT NULL,
                method TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                job_id TEXT PRIMARY KEY,
                discord_id TEXT NOT NULL,
                total_cents INTEGER NOT NULL,
                status TEXT NOT NULL,
                tracking_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_refunds (
                job_id TEXT PRIMARY KEY,
                discord_id TEXT NOT NULL,
                tracking_url TEXT NOT NULL,
                email TEXT NOT NULL,
                password TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'tracking',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def get_balance(discord_id: str) -> int:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT balance_cents FROM users WHERE discord_id = ?", (str(discord_id),)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def adjust_balance(discord_id: str, amount_cents: int) -> int:
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            INSERT INTO users (discord_id, balance_cents) VALUES (?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET balance_cents = balance_cents + ?
        """, (str(discord_id), max(0, amount_cents), amount_cents))
        await db.commit()
    return await get_balance(str(discord_id))

async def log_order(job_id: str, discord_id: str, total_cents: int, status: str, tracking_url: str = None):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            INSERT INTO orders (job_id, discord_id, total_cents, status, tracking_url)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET status = ?, tracking_url = ?
        """, (job_id, str(discord_id), total_cents, status, tracking_url, status, tracking_url))
        await db.commit()

async def queue_for_refund(job_id: str, discord_id: str, tracking_url: str, email: str, password: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            INSERT OR REPLACE INTO pending_refunds (job_id, discord_id, tracking_url, email, password, status)
            VALUES (?, ?, ?, ?, ?, 'tracking')
        """, (job_id, str(discord_id), tracking_url, email, password))
        await db.commit()

async def get_daily_volume():
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("""
            SELECT 
                COALESCE(SUM(total_cents), 0),
                COUNT(*)
            FROM orders 
            WHERE status = 'placed' 
              AND DATE(created_at, 'localtime') = DATE('now', 'localtime')
        """) as cur:
            row = await cur.fetchone()
            total_cents = row[0] if row else 0
            order_count = row[1] if row else 0
            return total_cents, order_count