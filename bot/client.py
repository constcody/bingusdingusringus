import discord
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    await bot.load_extension("bot.cogs.orders")
    await bot.load_extension("bot.cogs.wallet")

@bot.event
async def on_ready():
    # Sync globally so commands appear in DMs
    synced = await bot.tree.sync()
    print(f"  Synced {len(synced)} global command(s) across Discord.")
    print(f"  Discord bot logged in as {bot.user}")