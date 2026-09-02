import discord
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    # Load cogs during startup lifecycle
    await bot.load_extension("bot.cogs.orders")
    await bot.load_extension("bot.cogs.wallet")
    await bot.load_extension("bot.cogs.refund_cog")  # <-- Add this line

@bot.event
async def on_ready():
    # Syncs slash commands instantly to every guild the bot is currently in
    for guild in bot.guilds:
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"✅ Synced slash commands to server: {guild.name} ({guild.id})")
        
    print(f"🚀 Discord bot logged in as {bot.user}")