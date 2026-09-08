import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from database.db import get_balance, adjust_balance

# (Optional) Hardcode your user ID here if you want an absolute fallback
OWNER_IDS = []

# (Optional) Role ID that can manage balances
ADMIN_ROLE_ID = None

def is_authorized_admin(interaction: discord.Interaction) -> bool:
    """Checks if the user has Discord admin perms, the admin role, or is owner."""
    if interaction.user.id in OWNER_IDS:
        return True
    if ADMIN_ROLE_ID and any(role.id == ADMIN_ROLE_ID for role in getattr(interaction.user, "roles", [])):
        return True
    if getattr(interaction.user, "guild_permissions", None) and interaction.user.guild_permissions.administrator:
        return True
    return False

class WalletCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your own or another user's balance")
    @app_commands.describe(user="The user whose balance you want to check (defaults to yourself)")
    async def balance(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        target = user or interaction.user
        balance_cents = await get_balance(str(target.id))
        balance_usd = balance_cents / 100.0

        embed = discord.Embed(
            title="💳 Balance Details",
            color=discord.Color.green() if balance_usd > 0 else discord.Color.light_grey()
        )
        embed.set_author(name=target.display_name, icon_url=target.display_avatar.url)
        embed.add_field(name="User", value=target.mention, inline=True)
        embed.add_field(name="Current Balance", value=f"**${balance_usd:.2f}**", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="addbalance", description="Add funds to a user's wallet (Admin)")
    @app_commands.describe(user="The target user", amount="Dollar amount to add (e.g. 25.00)")
    @app_commands.default_permissions(administrator=True)
    async def add_balance_cmd(self, interaction: discord.Interaction, user: discord.User, amount: float):
        if not is_authorized_admin(interaction):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be greater than $0.00.", ephemeral=True)
            return

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

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="removebalance", description="Deduct funds from a user's wallet (Admin)")
    @app_commands.describe(user="The target user", amount="Dollar amount to deduct (e.g. 15.00)")
    @app_commands.default_permissions(administrator=True)
    async def remove_balance_cmd(self, interaction: discord.Interaction, user: discord.User, amount: float):
        if not is_authorized_admin(interaction):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be greater than $0.00.", ephemeral=True)
            return

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

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(WalletCog(bot))