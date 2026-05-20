import datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks
from main import GUILD_ID
from zoneinfo import ZoneInfo


class MessageScheduler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="schedule_message_at", description="Schedule a message to be sent at a specific date and time")
    @app_commands.guilds(GUILD_ID)
    async def schedule_message_at(self,
                                interaction: discord.Interaction,
                                message: str,
                                send_time: str,
                                ###send_date: str = datetime.date.today().isoformat(),
                                timezone: str = "Europe/Berlin"):
        await interaction.response.defer(ephemeral=True)

        try:
            target_dt = datetime.time.fromisoformat(f"{send_time}").replace(tzinfo=ZoneInfo(timezone))
        except Exception as e:
            await interaction.followup.send(f'An error occurred: {e}')
            return

    
        @tasks.loop(time=target_dt, count=1)
        async def scheduled_send():
            if isinstance(interaction.channel, (discord.TextChannel, discord.VoiceChannel, discord.Thread)):
                await interaction.channel.send(
                    interaction.user.display_name + " scheduled the message:\n" + message
                )
        scheduled_send.start()

        await interaction.followup.send(
            f"Message scheduled for {target_dt.isoformat()}"
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MessageScheduler(bot))