import discord
from discord import app_commands
from discord.ext import commands
from services.support_bot import automate_missing_items

class RefundCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="nj", description="Automatically refund a delivered order using account credentials")
    @app_commands.describe(credentials="Format: email:password:number")
    async def nj(self, interaction: discord.Interaction, credentials: str):
        await interaction.response.defer(ephemeral=True)

        parts = credentials.split(":")
        if len(parts) < 2:
            await interaction.followup.send("❌ Invalid format. Please use `email:password:number`.", ephemeral=True)
            return

        email = parts[0].strip()
        password = parts[1].strip()

        await interaction.followup.send(f"⏳ Launching automated refund workflow for `{email}`...", ephemeral=True)

        try:
            await automate_missing_items(email, password)
            await interaction.followup.send(f"✅ Completed refund process for `{email}`.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Refund execution failed: `{str(e)}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RefundCog(bot))