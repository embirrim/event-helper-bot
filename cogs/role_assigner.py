import discord
from discord import app_commands, TextChannel
from discord.ext import commands
from main import GUILD_ID
import sqlite3
import emoji as emoji_module

class RoleAssigner(commands.Cog):
    # map of (message_id, reaction_str) -> role_name
    ROLE_MAP: dict[tuple[int, str], str] = {}

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def is_role_message(self, message_id: int) -> bool:
        return any(message_id == stored_message_id for stored_message_id, _ in self.ROLE_MAP)
    

    async def role_name_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for role names"""
        all_roles = [role for role in interaction.guild.roles if current.lower() in role.name.lower()]
        return [app_commands.Choice(name=role.name, value=role.name) for role in all_roles[:25]]
    
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT message_id, reaction, role_name FROM role_assigner')
        rows = cursor.fetchall()
        ROLE_MAP = {(row[0], row[1]): row[2] for row in rows}
        conn.close()
    except Exception as e:
        ROLE_MAP = {}
        print(f"Error occurred while loading role assignment message IDs from database: {e}")


    @app_commands.command(name="post_role_message", description="Post a message in the channel that users can react to in order to get a role")
    @app_commands.guilds(GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(role_name=role_name_autocomplete)
    async def post_role_message(self, interaction: discord.Interaction, emoji: str, role_name: str):
        await interaction.response.defer(ephemeral=True)

        if interaction.channel is None or interaction.channel.type != discord.ChannelType.text:
            await interaction.followup.send("This command can only be used in text channels.", ephemeral=True)
            return
        
        if not emoji_module.is_emoji(emoji):
            await interaction.followup.send("Invalid emoji, please use a Unicode emoji.", ephemeral=True)
            return
        
        if role_name not in [role.name for role in interaction.guild.roles]:
            await interaction.followup.send(f"Role '{role_name}' does not exist in this server, did you use autocomplete?", ephemeral=True)
            return

        embed = discord.Embed(title="React to get a role!", description="React with the appropriate emoji to get the corresponding role.")
        embed.add_field(name=role_name, value=emoji, inline=True)
        message = await interaction.channel.send(embed=embed)

        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO role_assigner (message_id, reaction, role_name) VALUES (?, ?, ?)',
                          (message.id, emoji, role_name))
            conn.commit()
            conn.close()
            print(f"Inserted role assignment message {message.id} into database")
            self.ROLE_MAP[(message.id, emoji)] = role_name
        except Exception as e:
            print(f"Error occurred while inserting into database: {e}")

        await message.add_reaction(emoji)

        await interaction.followup.send(f"Role assignment message posted", ephemeral=True)

    


    @app_commands.command(name="edit_role_message", description="Edit a role message by adding or updating a role and reaction")
    @app_commands.guilds(GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        message_id="Message ID or Discord message link",
        emoji="Reaction emoji",
        role_name="Role name to assign to this emoji"
    )
    @app_commands.autocomplete(role_name=role_name_autocomplete)
    async def edit_role_message(
        self, 
        interaction: discord.Interaction,
        message_id: str,
        emoji: str,
        role_name: str,
    ):
        await interaction.response.defer(ephemeral=True)

        # Parse message_id from link if provided
        parsed_message_id = None
        if "discord.com/channels/" in message_id:
            # Extract message ID from Discord link
            try:
                parsed_message_id = int(message_id.split("/")[-1])
            except (ValueError, IndexError):
                await interaction.followup.send("Invalid Discord message link format.", ephemeral=True)
                return
        else:
            try:
                parsed_message_id = int(message_id)
            except ValueError:
                await interaction.followup.send("Invalid message ID. Please provide a valid ID or Discord message link.", ephemeral=True)
                return

        if parsed_message_id is None or not self.is_role_message(parsed_message_id):
            await interaction.followup.send("Message ID not found in role assignment messages.", ephemeral=True)
            return

        if interaction.channel is None or interaction.channel.type != discord.ChannelType.text:
            await interaction.followup.send("This command can only be used in text channels.", ephemeral=True)
            return
        
        if not emoji_module.is_emoji(emoji):
            await interaction.followup.send("Invalid emoji, please use a Unicode emoji.", ephemeral=True)
            return
        
        if role_name not in [role.name for role in interaction.guild.roles]:
            await interaction.followup.send(f"Role '{role_name}' does not exist in this server, did you use autocomplete?", ephemeral=True)
            return


        # Try to fetch the message
        if interaction.channel is None:
            await interaction.followup.send("Could not access the channel.", ephemeral=True)
            return

        try:
            if not isinstance(interaction.channel, TextChannel):
                await interaction.followup.send("This command can only be used in text channels.", ephemeral=True)
                return

            message = await interaction.channel.fetch_message(parsed_message_id)
        except discord.NotFound:
            await interaction.followup.send("Message not found.", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.followup.send("Cannot access this message.", ephemeral=True)
            return

        # Update database
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            
            # Check if this emoji already exists for this message
            cursor.execute('SELECT role_name FROM role_assigner WHERE message_id = ? AND reaction = ?',
                          (parsed_message_id, emoji))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing entry
                cursor.execute('UPDATE role_assigner SET role_name = ? WHERE message_id = ? AND reaction = ?',
                              (role_name, parsed_message_id, emoji))
            else:
                # Insert new entry
                cursor.execute('INSERT INTO role_assigner (message_id, reaction, role_name) VALUES (?, ?, ?)',
                              (parsed_message_id, emoji, role_name))
            
            conn.commit()
            conn.close()
            # update in-memory cache
            self.ROLE_MAP[(parsed_message_id, emoji)] = role_name
            print(f"Updated role assignment: message {parsed_message_id}, emoji {emoji}, role {role_name}")
        except Exception as e:
            await interaction.followup.send(f"Error updating database: {e}", ephemeral=True)
            return

        # Update the embed
        if message.embeds:
            embed = message.embeds[0]
        else:
            embed = discord.Embed(title="React to get a role!", description="React with the appropriate emoji to get the corresponding role.")
        
        # Update or add the field for this emoji
        field_name = emoji
        field_value = role_name
        
        # Check if field already exists and update it
        field_found = False
        for i, field in enumerate(embed.fields):
            if field.name == emoji:
                embed.set_field_at(i, name=field_name, value=field_value, inline=True)
                field_found = True
                break
        
        if not field_found:
            embed.add_field(name=field_name, value=field_value, inline=True)

        # Edit the message
        try:
            await message.edit(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"Error updating message: {e}", ephemeral=True)
            return

        # Add the reaction if not already present
        try:
            await message.add_reaction(emoji)
        except Exception as e:
            print(f"Error adding reaction: {e}")

        await interaction.followup.send(f"Role message updated: {emoji} now assigns **{role_name}**", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if self.bot.user is not None and payload.user_id == self.bot.user.id:
            return

        if not self.is_role_message(payload.message_id):
            return

        if payload.guild_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        # Look up role name from in-memory cache for this specific message and emoji
        key = (payload.message_id, str(payload.emoji))
        role_name = self.ROLE_MAP.get(key)
        if role_name is None:
            print(f"No role mapping found for message {payload.message_id} and reaction {payload.emoji}")
            return

        role = discord.utils.get(guild.roles, name=role_name)
        member = guild.get_member(payload.user_id)
        if role is not None and member is not None:
            print(f"Assigning role {role_name} to user {member.name} for reaction {payload.emoji} on message {payload.message_id}")
            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if self.bot.user is not None and payload.user_id == self.bot.user.id:
            return

        if not self.is_role_message(payload.message_id):
            return

        if payload.guild_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        # Look up role name from in-memory cache for this specific message and emoji
        key = (payload.message_id, str(payload.emoji))
        role_name = self.ROLE_MAP.get(key)
        if role_name is None:
            print(f"No role mapping found for message {payload.message_id} and reaction {payload.emoji}")
            return

        role = discord.utils.get(guild.roles, name=role_name)
        member = guild.get_member(payload.user_id)
        if role is not None and member is not None:
            print(f"Removing role {role_name} from user {member.name} for reaction {payload.emoji} on message {payload.message_id}")
            await member.remove_roles(role)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleAssigner(bot))