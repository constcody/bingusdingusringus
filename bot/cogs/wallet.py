import time
import asyncio
import urllib.parse
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from config.settings import settings
from database.db import get_balance, adjust_balance
import aiohttp

ACTIVE_POLLS = set()

async def poll_payment_status(bot: commands.Bot, payment_id: str, discord_id: str, amount_cents: int):
    """Polls NOWPayments status using x-api-key and auto-credits the balance."""
    headers = {
        "x-api-key": settings.NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }

    print(f"[Polling Started] Tracking Payment ID {payment_id} for user {discord_id}...")

    # Poll every 8 seconds for up to 30 minutes (225 checks)
    for i in range(225):
        await asyncio.sleep(8)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.nowpayments.io/v1/payment/{payment_id}", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        p_status = data.get("payment_status")
                        print(f"[Poll #{i+1}] Payment {payment_id} status: {p_status}")

                        if p_status in ["finished", "confirmed", "paid", "sending"]:
                            await adjust_balance(discord_id, amount_cents)
                            print(f"✅ [Deposit Complete] User {discord_id} credited with ${amount_cents / 100:.2f}")

                            try:
                                user = await bot.fetch_user(int(discord_id))
                                if user:
                                    await user.send(f"✅ **Deposit Confirmed!**\n**${amount_cents / 100:.2f}** has been automatically added to your balance.")
                            except Exception as dm_err:
                                print(f"[DM Error]: {dm_err}")
                            return
                        elif p_status in ["failed", "refunded", "expired"]:
                            print(f"❌ Payment {payment_id} ended with status: {p_status}")
                            return
                    else:
                        err_body = await resp.text()
                        print(f"[Poll #{i+1}] HTTP {resp.status} checking payment {payment_id}: {err_body}")
        except Exception as e:
            print(f"[Poll Exception]: {e}")

class WalletCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your current bot balance")
    async def balance(self, interaction: discord.Interaction):
        cents = await get_balance(str(interaction.user.id))
        await interaction.response.send_message(f"💳 Available balance: **${cents / 100:.2f}**", ephemeral=True)

    @app_commands.command(name="deposit", description="Deposit credits using Crypto")
    @app_commands.describe(amount="Deposit amount in USD")
    async def deposit(self, interaction: discord.Interaction, amount: float):
        if amount < 5.00:
            await interaction.response.send_message("Minimum deposit is $5.00.", ephemeral=True)
            return

        amount_cents = int(amount * 100)
        await interaction.response.defer(ephemeral=True)

        headers = {
            "x-api-key": settings.NOWPAYMENTS_API_KEY,
            "Content-Type": "application/json"
        }

        order_id = f"deposit_{interaction.user.id}_{int(time.time())}"
        payload = {
            "price_amount": amount,
            "price_currency": "usd",
            "pay_currency": "sol",
            "order_id": order_id,
            "order_description": f"Deposit ${amount:.2f} for user {interaction.user.id}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.nowpayments.io/v1/payment", json=payload, headers=headers) as resp:
                    data = await resp.json()
                    if resp.status in [200, 201]:
                        payment_id = str(data.get("payment_id"))
                        pay_address = data.get("pay_address")
                        pay_amount = data.get("pay_amount")

                        if not payment_id or not pay_address:
                            await interaction.followup.send(f"❌ API Error: {data}", ephemeral=True)
                            return

                        # Launch background poller with strong reference
                        task = asyncio.create_task(
                            poll_payment_status(self.bot, payment_id, str(interaction.user.id), amount_cents)
                        )
                        ACTIVE_POLLS.add(task)
                        task.add_done_callback(ACTIVE_POLLS.discard)

                        # Generate QR code for Phantom/mobile scanning
                        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(pay_address)}"

                        embed = discord.Embed(title="🪙 Solana (SOL) Deposit", color=discord.Color.gold())
                        embed.add_field(name="💵 USD Amount", value=f"**${amount:.2f}**", inline=True)
                        embed.add_field(name="🟣 Amount to Send", value=f"**{pay_amount} SOL**", inline=True)
                        embed.add_field(name="📫 Deposit Address (Tap/Click to Copy)", value=f"```{pay_address}```", inline=False)
                        embed.set_thumbnail(url=qr_url)
                        embed.set_footer(text="Send the exact SOL amount to the address above. Balance updates automatically upon blockchain confirmation.")

                        await interaction.followup.send(embed=embed, ephemeral=True)
                    else:
                        await interaction.followup.send(f"❌ Failed to create deposit (Status {resp.status}): {data}", ephemeral=True)
        except Exception as e:
            print(f"[Deposit Error]: {e}")
            await interaction.followup.send("❌ An error occurred while generating the payment.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(WalletCog(bot))