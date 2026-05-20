import discord
from discord import app_commands
from discord.ext import commands
from main import GUILD_ID


class EventCreator(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="create_event", description="Create role, category, and channels for an event")
    @app_commands.guilds(GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    async def create_event(self, interaction: discord.Interaction, event_name: str):
        await interaction.response.defer(ephemeral=True)
        assert interaction.guild is not None

        if discord.utils.get(interaction.guild.categories, name=event_name):
            await interaction.followup.send("Event category already exists!")
            return

        try:
            event_it_role = discord.utils.get(interaction.guild.roles, name="Event IT")
            bot_role = discord.utils.get(interaction.guild.roles, name="Bot")
            event_role = await interaction.guild.create_role(name=event_name)
            event_category = await interaction.guild.create_category(name=event_name)

            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    view_channel=False,
                    read_messages=False,
                    connect=False,
                ),
                event_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    connect=True,
                    speak=True,
                ),
                event_it_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    connect=True,
                    speak=True,
                ),
                bot_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    connect=True,
                    speak=True,
                ),
            }
            await event_category.edit(overwrites=overwrites)

            event_text_channels = [
                "announcements-and-call-times",
                "general",
                "network",
                "offtopic",
            ]
            for channel_name in event_text_channels:
                await interaction.guild.create_text_channel(name=channel_name, category=event_category)

            event_voice_channels = [
                "voice-and-remote-support",
            ]
            for channel_name in event_voice_channels:
                await interaction.guild.create_voice_channel(name=channel_name, category=event_category)

            event_forum_channels = [
                "setup-forum",
            ]
            for channel_name in event_forum_channels:
                await interaction.guild.create_forum(name=channel_name, category=event_category)

            await interaction.followup.send(f"Role, category, and channels created for event: {event_name}")
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EventCreator(bot))