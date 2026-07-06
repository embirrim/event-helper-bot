import asyncio
import discord
from discord.ext import tasks, commands
from discord.ext.commands import has_permissions
from discord import app_commands
import os
import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import database

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = discord.Object(id=int(os.getenv("GUILD_ID", "0")))

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True 
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents = intents)

@bot.event
async def on_ready():
     print(f'Logged in as {bot.user}')

     try:
          synced = await bot.tree.sync(guild=GUILD_ID)
          print(f'Synced {len(synced)} commands to guild {GUILD_ID.id}')

     except Exception as e:
          print(f'Error: {e}')


async def main():
    database.setup()

    ## await bot.load_extension('cogs.event_creator')
    ## await bot.load_extension('cogs.message_scheduler')
    ## await bot.load_extension('cogs.user_settings')
    ## await bot.load_extension('cogs.role_assigner')
    await bot.load_extension('cogs.message_summarizer')

    try:
        assert TOKEN is not None, "DISCORD_TOKEN environment variable not set"
        await bot.start(TOKEN)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print('Received stop signal, shutting down bot...')
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == '__main__':
    asyncio.run(main())