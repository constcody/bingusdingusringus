import time
import asyncio
import urllib.parse
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import aiohttp

from config.settings import settings
from database.db import get_balance, adjust_balance

ACTIVE_POLLS = set()

OWNER_IDS = []
ADMIN_ROLE_ID = None

def is_authorized_admin(interaction: discord.Interaction) -> bool:
    if interaction.user.id in OWNER_IDS:
        return True
    if ADMIN_ROLE_ID and any(role.id == ADMIN_ROLE_ID for role in getattr(interaction.user, "roles", [])):
        return True
    if getattr(interaction.user, "guild_permissions", None) and interaction.user.guild_permissions.administrator:
        return True
    return False

async def poll_payment_status(bot: commands.Bot, payment_id: str, discord_id: str, amount_cents: int):
    """Polls NOWPayments status using x-api-key and auto-credits the balance."""
    headers = {
        "x-api-key": settings.NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }
    print(f"[Polling Started] Tracking Payment ID {payment_id} for user {discord_id}...")

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
                            print(f"  [Deposit Complete] User {discord_id} credited with ${amount_cents / 100:.2f}")
                            try:
                                user = await bot.fetch_user(int(discord_id))
                                if user:
                                    await user.send(
                                        f"✅ **Deposit Confirmed!**\n**${amount_cents / 100:.2f}** has been automatically added to your balance."
                                    )
                            except Exception as dm_err:
                                print(f"[DM Error]: {dm_err}")
                            return
                        elif p_status in ["failed", "refunded", "expired"]:
                            print(f"  Payment {payment_id} ended with status: {p_status}")
                            return
                    else:
                        err_body = await resp.text()
                        print(f"[Poll #{i+1}] HTTP {resp.status} checking payment {payment_id}: {err_body}")
        except Exception as e:
            print(f"[Poll Exception]: {e}")

class WalletCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your own or another user's balance")
    @app_commands.describe(user="The user whose balance you want to check (defaults to yourself)")
    async def balance(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        target = user or interaction.user
        cents = await get_balance(str(target.id))
        balance_usd = cents / 100.0

        embed = discord.Embed(
            title="💳 Balance Details",
            color=discord.Color.green() if balance_usd > 0 else discord.Color.light_grey()
        )
        embed.set_author(name=target.display_name, icon_url=target.display_avatar.url)
        embed.add_field(name="User", value=target.mention, inline=True)
        embed.add_field(name="Current Balance", value=f"**${balance_usd:.2f}**", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="deposit", description="Deposit credits using Crypto")
    @app_commands.describe(amount="Deposit amount in USD")
    async def deposit(self, interaction: discord.Interaction, amount: float):
        if amount < 5.00:
            await interaction.response.send_message("❌ Minimum deposit is $5.00.", ephemeral=True)
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
                            await interaction.followup.send(f"❌ API Error: `{data}`", ephemeral=True)
                            return

                        task = asyncio.create_task(
                            poll_payment_status(self.bot, payment_id, str(interaction.user.id), amount_cents)
                        )
                        ACTIVE_POLLS.add(task)
                        task.add_done_callback(ACTIVE_POLLS.discard)

                        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(pay_address)}"

                        embed = discord.Embed(title="⚡ Solana (SOL) Deposit", color=discord.Color.gold())
                        embed.add_field(name="USD Amount", value=f"**${amount:.2f}**", inline=True)
                        embed.add_field(name="Amount to Send", value=f"**{pay_amount} SOL**", inline=True)
                        embed.add_field(name="Deposit Address (Tap/Click to Copy)", value=f"```{pay_address}```", inline=False)
                        embed.set_thumbnail(url=qr_url)
                        embed.set_footer(text="Send the exact SOL amount to the address above. Balance updates automatically upon blockchain confirmation.")

                        await interaction.followup.send(embed=embed, ephemeral=True)
                    else:
                        await interaction.followup.send(f"❌ Failed to create deposit (Status {resp.status}): `{data}`", ephemeral=True)
        except Exception as e:
            print(f"[Deposit Error]: {e}")
            await interaction.followup.send("❌ An error occurred while generating the payment.", ephemeral=True)

    @app_commands.command(name="addbalance", description="Add funds to a user's wallet (Admin)")
    @app_commands.describe(user="The target user", amount="Dollar amount to add (e.g. 25.00)")
    @app_commands.default_permissions(administrator=True)
    async def add_balance_cmd(self, interaction: discord.Interaction, user: discord.User, amount: float):
        await interaction.response.defer(ephemeral=True)

        if not is_authorized_admin(interaction):
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.followup.send("❌ Amount must be greater than $0.00.", ephemeral=True)
            return

        try:
            amount_cents = int(round(amount * 100))
            new_balance_cents = await adjust_balance(str(user.id), amount_cents)
            new_balance_usd = new_balance_cents / 100.0

            embed = discord.Embed(
                title="✅ Balance Added",
                color=discord.Color.green()
            )
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
            embed.add_field(name="User", value=user.mention, inline=True)
            embed.add_field(name="Amount Added", value=f"+${amount:.2f}", inline=True)
            embed.add_field(name="New Total", value=f"**${new_balance_usd:.2f}**", inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"[AddBalance Error]: {e}")
            await interaction.followup.send(f"❌ Failed to update balance: `{e}`", ephemeral=True)

    @app_commands.command(name="removebalance", description="Deduct funds from a user's wallet (Admin)")
    @app_commands.describe(user="The target user", amount="Dollar amount to deduct (e.g. 15.00)")
    @app_commands.default_permissions(administrator=True)
    async def remove_balance_cmd(self, interaction: discord.Interaction, user: discord.User, amount: float):
        await interaction.response.defer(ephemeral=True)

        if not is_authorized_admin(interaction):
            await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.followup.send("❌ Amount must be greater than $0.00.", ephemeral=True)
            return

        try:
            amount_cents = -int(round(amount * 100))
            new_balance_cents = await adjust_balance(str(user.id), amount_cents)
            new_balance_usd = new_balance_cents / 100.0

            embed = discord.Embed(
                title="🔻 Balance Deducted",
                color=discord.Color.red()
            )
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
            embed.add_field(name="User", value=user.mention, inline=True)
            embed.add_field(name="Amount Deducted", value=f"-${amount:.2f}", inline=True)
            embed.add_field(name="New Total", value=f"**${new_balance_usd:.2f}**", inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"[RemoveBalance Error]: {e}")
            await interaction.followup.send(f"❌ Failed to update balance: `{e}`", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(WalletCog(bot))