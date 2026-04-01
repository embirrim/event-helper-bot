import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from discord import app_commands

class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged in as {self.user}')

        try:
             guild = discord.Object(id=471950858079436801)
             synced = await self.tree.sync(guild=guild)
             print(f'Synced {len(synced)} commands to guild {guild.id}')

        except Exception as e:
             print(f'Error: {e}')



intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True 
intents.guilds = True
intents.members = True

client = Client(command_prefix="!", intents = intents)

GUILD_ID = discord.Object(id=471950858079436801)


@client.tree.command(name="create_event", description="create role, category, and channels for an event", guild=GUILD_ID)
@app_commands.default_permissions(administrator = True)
async def create_event(interaction: discord.Interaction, event_name: str):
     await interaction.response.defer(ephemeral = True)
     if discord.utils.get(interaction.guild.categories, name = event_name):
          return
     
     try:
          event_role = await interaction.guild.create_role(name = event_name)
          event_category = await interaction.guild.create_category(name = event_name)
          overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(view_channel = False, read_messages=False, connect=False),
                    event_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True)
                    }
          await event_category.edit(overwrites = overwrites)
          event_text_channels = [
               "general",
               "network",
               "test"
          ]
          for channel in event_text_channels:
               await interaction.guild.create_text_channel(name = channel, category = event_category)
          
          await interaction.followup.send("Role, category, and channels created!")
     except Exception as e:
          await interaction.response.edit_message(f'An error occurred: {e}')

     

        
        
        
client.run("MTQ4MzU4NzA4ODY0MDExNDczOQ.GNutUt.Luhc2g3YpRscpE0TBamaGVETHfGEEAZLKQbtAQ")