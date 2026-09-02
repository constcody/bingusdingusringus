import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from bot.views.order_modal import OrderModal

class FulfillmentSelectView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="Delivery", emoji="🚚", style=discord.ButtonStyle.primary)
    async def delivery_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(OrderModal(fulfillment="delivery"))

    @discord.ui.button(label="Pickup", emoji="🥡", style=discord.ButtonStyle.secondary)
    async def pickup_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(OrderModal(fulfillment="pickup"))

class OrdersCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="order", description="Start a new DoorDash discounted order")
    async def order(self, interaction: discord.Interaction):
        view = FulfillmentSelectView()
        await interaction.response.send_message(
            "Select your fulfillment method to begin:",
            view=view,
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(OrdersCog(bot))