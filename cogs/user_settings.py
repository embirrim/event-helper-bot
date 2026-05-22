import datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks
from main import GUILD_ID
from zoneinfo import available_timezones
import sqlite3

async def timezone_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    timezones = sorted(available_timezones())
    return [
        app_commands.Choice(name=tz, value=tz)
        for tz in timezones
        if current.lower() in tz.lower()
    ][:25]



class TimezoneSetter(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @app_commands.command(name="set_timezone", description="Set your preferred timezone")
    @app_commands.guilds(GUILD_ID)
    @app_commands.autocomplete(timezone=timezone_autocomplete)
    async def set_timezone(self, interaction: discord.Interaction, timezone: str):
        await interaction.response.defer(ephemeral=True)

        if timezone not in available_timezones():
            await interaction.followup.send("Invalid timezone. Please select a valid timezone from the autocomplete suggestions.")
            return

        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO user_settings (user_id, timezone) VALUES (?, ?)
                              ON CONFLICT(user_id) DO UPDATE SET timezone=excluded.timezone''',
                           (interaction.user.id, timezone))
            conn.commit()
            conn.close()
            await interaction.followup.send(f"Your timezone has been set to {timezone}.")
        except Exception as e:
            await interaction.followup.send(f'An error occurred while setting your timezone: {e}')




async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TimezoneSetter(bot))