import discord
from discord.ext import tasks, commands
from discord.ext.commands import has_permissions
from discord import app_commands
import os
import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = discord.Object(id=os.getenv("GUILD_ID"))

class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged in as {self.user}')

        try:
             synced = await self.tree.sync(guild=GUILD_ID)
             print(f'Synced {len(synced)} commands to guild {GUILD_ID.id}')

        except Exception as e:
             print(f'Error: {e}')



intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True 
intents.guilds = True
intents.members = True

client = Client(command_prefix="!", intents = intents)



@client.tree.command(name="create_event", description="create role, category, and channels for an event", guild=GUILD_ID)
@app_commands.default_permissions(administrator = True)
async def create_event(interaction: discord.Interaction, event_name: str):
     await interaction.response.defer(ephemeral = True)
     if discord.utils.get(interaction.guild.categories, name = event_name):
          await interaction.followup.send("Event name already exists!")
          return
     
     try:
          event_it_role = discord.utils.get(interaction.guild.roles, name = "Event IT")
          bot_role = discord.utils.get(interaction.guild.roles, name = "Bot")
          event_role = await interaction.guild.create_role(name = event_name)
          event_category = await interaction.guild.create_category(name = event_name)
          overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(view_channel = False, read_messages=False, connect=False),
                    event_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True),
                    event_it_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True),
                    bot_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True)
                    }
          await event_category.edit(overwrites = overwrites)
          event_text_channels = [
               "announcements-and-call-times",
               "general",
               "network",
               "offtopic"
          ]
          for channel in event_text_channels:
               channel = await interaction.guild.create_text_channel(name = channel, category = event_category)
          
          event_voice_channels = [
               "voice-and-remote-support",
          ]
          for channel in event_voice_channels:
               channel = await interaction.guild.create_voice_channel(name = channel, category = event_category)

          
          event_forum_channels = [
               "setup-forum",
          ]
          for channel in event_forum_channels:
               await interaction.guild.create_forum(name = channel, category = event_category)


          
          await interaction.followup.send(f'Role, category, and channels created for event: {event_name}')
     except Exception as e:
          await interaction.followup.send(f'An error occurred: {e}')

     

@client.tree.command(name="schedule_message_at", description="Schedule a message to be sent later", guild=GUILD_ID)
async def schedule_message_at(interaction: discord.Interaction,
                              message: str,
                              send_time: str,
                              send_date: str = datetime.date.today().isoformat(),
                              timezone: str = "Europe/Berlin"):
    await interaction.response.defer(ephemeral=True)
    try:
        target_dt = datetime.datetime.fromisoformat(f"{send_date}T{send_time}").replace(tzinfo=ZoneInfo(timezone))
    except Exception as e:
        await interaction.followup.send(f'An error occurred: {e}')
        return

   
    @tasks.loop(time=target_dt, count=1)
    async def scheduled_send():
        await interaction.channel.send(
            interaction.user.display_name + " scheduled the message:\n" + message
        )
    scheduled_send.start()

    await interaction.followup.send(
        f"Message scheduled for {target_dt.isoformat()}"
    )


client.run(TOKEN)