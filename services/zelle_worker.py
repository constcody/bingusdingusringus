import asyncio
import imaplib
import email
import re
import aiosqlite
from config.settings import settings
from database.db import DB_FILE, adjust_balance

async def check_zelle_emails(bot):
    # Only run if IMAP credentials are provided
    if not settings.IMAP_USER or not settings.IMAP_PASS:
        print("[Zelle Worker] IMAP credentials missing in .env. Skipping background worker.")
        return

    while True:
        try:
            # Connect via SSL
            mail = imaplib.IMAP4_SSL(settings.IMAP_HOST)
            mail.login(settings.IMAP_USER, settings.IMAP_PASS)
            mail.select("inbox")

            status, messages = mail.search(None, '(UNSEEN SUBJECT "Zelle")')
            if status == "OK":
                for num in messages[0].split():
                    if not num:
                        continue
                    res, data = mail.fetch(num, "(RFC822)")
                    msg = email.message_from_bytes(data[0][1])
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")

                    # Extract dollar amount and memo reference code (e.g. ZEL-8492)
                    amount_match = re.search(r"\$([0-9]+(?:\.[0-9]{2})?)", body)
                    ref_match = re.search(r"ZEL-[A-Z0-9]{4,6}", body, re.IGNORECASE)

                    if amount_match and ref_match:
                        amount_cents = int(float(amount_match.group(1)) * 100)
                        ref_code = ref_match.group(0).upper()

                        async with aiosqlite.connect(DB_FILE) as db:
                            async with db.execute(
                                "SELECT discord_id, amount_cents FROM pending_deposits WHERE ref_code = ? AND status = 'pending'",
                                (ref_code,)
                            ) as cur:
                                deposit = await cur.fetchone()

                            if deposit:
                                user_id, expected_cents = deposit
                                # Credit the user
                                await adjust_balance(user_id, amount_cents)
                                await db.execute("UPDATE pending_deposits SET status = 'completed' WHERE ref_code = ?", (ref_code,))
                                await db.commit()

                                # Send DM notification to user in Discord
                                try:
                                    user = await bot.fetch_user(int(user_id))
                                    if user:
                                        await user.send(f"✅ Your Zelle deposit of **${amount_cents / 100:.2f}** has been credited to your balance!")
                                except Exception as e:
                                    print(f"[Zelle Worker DM Error]: {e}")

            mail.logout()
        except Exception as e:
            print(f"[Zelle Worker Exception]: {e}")

        # Poll inbox every 15 seconds
        await asyncio.sleep(15)