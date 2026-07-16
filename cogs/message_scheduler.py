import datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks
from main import GUILD_ID
from zoneinfo import ZoneInfo
import dateparser
import sqlite3


class MessageScheduler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.recurring_tasks = {}
        self._recurring_messages_loaded = False

    async def _get_channel(self, channel_id: int):
        try:
            return await self.bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
            print(f'Unable to resolve channel {channel_id}: {e}')
            return None

    async def cog_load(self):
        self.message_scheduler.start()

    async def _load_recurring_messages(self):
        if self._recurring_messages_loaded:
            return

        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id, channel_id, user_name, message_content, send_at FROM recurring_messages')
            recurring_messages = cursor.fetchall()

            for recurring_id, channel_id, user_name, message_content, send_at in recurring_messages:
                channel = await self._get_channel(channel_id)
                if channel is not None and isinstance(channel, discord.abc.Messageable):
                    target_dt = datetime.datetime.fromtimestamp(send_at, tz=ZoneInfo("UTC"))
                    target_time = target_dt.timetz()
                    recurring_task = self._create_recurring_message_task(
                        channel=channel,
                        message=message_content,
                        user_name=user_name,
                        target_time=target_time,
                        timezone_name="UTC",
                        recurring_id=recurring_id,
                    )
                    self.recurring_tasks[recurring_id] = recurring_task
                else:
                    print(f'Channel {channel_id} not found or is not messageable.')
        except Exception as e:
            print(f'Error loading recurring messages from database: {e}')
        finally:
            conn.close()

        self._recurring_messages_loaded = True
    
    async def cog_unload(self):
        self.message_scheduler.cancel()
        for task in self.recurring_tasks.values():
            task.cancel()

    def _create_recurring_message_task(self, channel, message, user_name, target_time, timezone_name=None, recurring_id=None):
        if target_time is not None and target_time.tzinfo is None and timezone_name:
            target_time = target_time.replace(tzinfo=ZoneInfo(timezone_name))

        @tasks.loop(time=target_time)
        async def send_recurring_message():
            try:
                await channel.send(f'{user_name} scheduled this recurring message:\n{message}')
                print(f'Sent recurring message to channel {channel.id} at {datetime.datetime.now(ZoneInfo("UTC"))}')
            except Exception as e:
                print(f'Error sending recurring message: {e}')

        send_recurring_message.start()
        if recurring_id is not None:
            self.recurring_tasks[recurring_id] = send_recurring_message
        return send_recurring_message





    @tasks.loop(seconds=30)
    async def message_scheduler(self):
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, user_id,channel_id, message_content, send_at FROM scheduled_messages WHERE send_at <= ?''', (int(datetime.datetime.now(datetime.timezone.utc).timestamp()),))
            messages_to_send = cursor.fetchall()

            for msg_id, user_id, channel_id, message_content, send_at in messages_to_send:
                channel = await self._get_channel(channel_id)
                if channel is None:
                    print(f'Channel {channel_id} not found.')
                elif isinstance(channel, discord.abc.Messageable):
                    try:
                        await channel.send(f'{user_id} scheduled this message:\n{message_content}')
                    except Exception as e:
                        print(f'Error sending message to channel {channel_id}: {e}')
                else:
                    print(f'Channel {channel_id} is not messageable.')

                cursor.execute('DELETE FROM scheduled_messages WHERE id = ?', (msg_id,))
            conn.commit()
        except Exception as e:
            print(f'Error in message scheduler: {e}')
        finally:
            conn.close()

    @message_scheduler.before_loop
    async def before_message_scheduler(self):
        await self.bot.wait_until_ready()
        await self._load_recurring_messages()



    @app_commands.command(name="schedule_message_at", description="Schedule a message to be sent at a specific date and time")
    @app_commands.guilds(GUILD_ID)
    async def schedule_message_at(self,
                                interaction: discord.Interaction,
                                message: str,
                                send_at: str,):
        await interaction.response.defer(ephemeral=True)
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT timezone FROM user_settings WHERE user_id = ?', (interaction.user.id,))
            result = cursor.fetchone()
            timezone = result[0] if result else 'UTC'
            conn.close()
        except Exception as e:
            await interaction.followup.send(f'An error occurred while retrieving your timezone: {e}')
            return

        try:
            target_dt = dateparser.parse(send_at, settings={'TIMEZONE': timezone, 'RETURN_AS_TIMEZONE_AWARE': True})
        except Exception as e:
            await interaction.followup.send(f'An error occurred: {e}')
            return
    
        if target_dt is None:
                await interaction.followup.send("Sorry, I couldn't understand the date and time you provided. Please make sure to use a valid format.")
        elif not isinstance(interaction.channel, discord.TextChannel):
            await interaction.followup.send("This command can only be used in a text channel.")
        elif target_dt < datetime.datetime.now(ZoneInfo(timezone)):
            await interaction.followup.send("The specified date and time is in the past. Please provide a future date and time.")
        else:
            try:
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute('''INSERT INTO scheduled_messages (channel_id, user_id, message_content, send_at) VALUES (?, ?, ?, ?)''',
                                (interaction.channel_id, interaction.user.display_name, message, int(target_dt.astimezone(datetime.timezone.utc).timestamp())))
                conn.commit()
                conn.close()
                await interaction.followup.send(
                    f"I will send the following message at {target_dt}:\n\n{message}"
                )
            except Exception as e:
                await interaction.followup.send(f'An error occurred while scheduling the message: {e}')
    
    @app_commands.command(name="schedule_recurring_message_at", description="Schedule a recurring message to be sent at a specific time each day")
    @app_commands.guilds(GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    async def schedule_recurring_message_at(self,
                                interaction: discord.Interaction,
                                message: str,
                                send_at: str):
        await interaction.response.defer(ephemeral=True)
        
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT timezone FROM user_settings WHERE user_id = ?', (interaction.user.id,))
            result = cursor.fetchone()
            timezone = result[0] if result else 'UTC'
            conn.close()
        except Exception as e:
            await interaction.followup.send(f'An error occurred while retrieving your timezone: {e}')
            return

        try:
            target_dt = dateparser.parse(send_at, settings={'TIMEZONE': timezone, 'RETURN_AS_TIMEZONE_AWARE': True})
        except Exception as e:
            await interaction.followup.send(f'An error occurred: {e}')
            return

        if target_dt is None:
            await interaction.followup.send("Sorry, I couldn't understand the time you provided. Please make sure to use a valid format.")
            return
        elif not isinstance(interaction.channel, discord.TextChannel):
            await interaction.followup.send("This command can only be used in a text channel.")
            return

        target_time = target_dt.timetz()
        
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO recurring_messages (channel_id, user_name, message_content, send_at) VALUES (?, ?, ?, ?)''',
                            (interaction.channel_id, interaction.user.display_name, message, int(target_dt.astimezone(datetime.timezone.utc).timestamp())))
            recurring_id = cursor.lastrowid
            conn.commit()
            conn.close()
        except Exception as e:
            await interaction.followup.send(f'An error occurred while scheduling the recurring message: {e}')
            return
        
        recurring_task = self._create_recurring_message_task(
            channel=interaction.channel,
            message=message,
            user_name=interaction.user.display_name,
            target_time=target_time,
            timezone_name=timezone,
            recurring_id=recurring_id,
        )
        self.recurring_tasks[recurring_id] = recurring_task

        await interaction.followup.send(
            f"I will send the following recurring message every day at {target_time} {timezone}:\n\n{message}\n\nID: {recurring_id}"
        )

    @app_commands.command(name="cancel_recurring_message", description="Cancel a recurring message by its ID")
    @app_commands.guilds(GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    async def cancel_recurring_message(self, interaction: discord.Interaction, recurring_id: int):
        await interaction.response.defer(ephemeral=True)

        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM recurring_messages WHERE id = ? AND channel_id = ?', (recurring_id, interaction.channel_id))
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
        except Exception as e:
            await interaction.followup.send(f'An error occurred while canceling the recurring message: {e}')
            return

        task = self.recurring_tasks.pop(recurring_id, None)
        if task is not None:
            task.cancel()

        if deleted == 0:
            await interaction.followup.send(f'No recurring message with ID {recurring_id} was found in this channel.')
        else:
            await interaction.followup.send(f'Canceled recurring message {recurring_id}.')


    @app_commands.command(name="list_recurring_messages", description="List all recurring messages in this channel")
    @app_commands.guilds(GUILD_ID)
    @app_commands.default_permissions(administrator=True)
    async def list_recurring_messages(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id, user_name, message_content, send_at FROM recurring_messages WHERE channel_id = ?', (interaction.channel_id,))
            recurring_messages = cursor.fetchall()
            conn.close()
        except Exception as e:
            await interaction.followup.send(f'An error occurred while retrieving recurring messages: {e}')
            return

        if not recurring_messages:
            await interaction.followup.send("There are no recurring messages scheduled in this channel.")
            return

        message_list = []
        for recurring_id, user_name, message_content, send_at in recurring_messages:
            target_dt = datetime.datetime.fromtimestamp(send_at, tz=ZoneInfo("UTC"))
            message_list.append(f"ID: {recurring_id}, User: {user_name}, Time (UTC): {target_dt}, Message: {message_content}")

        await interaction.followup.send("\n".join(message_list))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MessageScheduler(bot))