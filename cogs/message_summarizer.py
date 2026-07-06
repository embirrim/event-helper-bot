import discord
from discord import app_commands, TextChannel
from discord.ext import commands
from main import GUILD_ID
import dateparser

class MessageSummarizer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="summarize", description=".")
    @app_commands.guilds(GUILD_ID)
    async def summarize(self, interaction: discord.Interaction, since: str):
        await interaction.response.defer(ephemeral=True)

        channel: TextChannel = interaction.channel
        since_time = dateparser.parse(since, settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True})

        if since_time is None:
            await interaction.followup.send("Could not parse the `since` timestamp. Please provide a valid date/time.")
            return

        try:
            async for message in channel.history(after=since_time):
                print(f'{message.author} sent {message.content} at {message.created_at}')
        except Exception as e:
            print(f"Error occurred while summarizing messages: {e}")

        await interaction.followup.send("Finished")

    # def summarize_messages(self, messages):
    #     # Placeholder for actual summarization logic
    #     for message in messages:
    #         print(message.content)  # Replace with actual summarization logic
    #     return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MessageSummarizer(bot))