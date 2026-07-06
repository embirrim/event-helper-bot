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
        self.recurring_tasks = []
    
    async def cog_load(self):
        self.message_scheduler.start()
    
    async def cog_unload(self):
        self.message_scheduler.cancel()
        for task in self.recurring_tasks:
            task.cancel()

    def _create_recurring_message_task(self, channel, message, user_name, target_time):
        @tasks.loop(time=target_time)
        async def send_recurring_message():
            try:
                await channel.send(f'{user_name} scheduled this recurring message:\n{message}')
            except Exception as e:
                print(f'Error sending recurring message: {e}')

        send_recurring_message.start()
        return send_recurring_message


    @tasks.loop(seconds=30)
    async def message_scheduler(self):
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, user_id,channel_id, message_content, send_at FROM scheduled_messages WHERE send_at <= ?''', (int(datetime.datetime.now(datetime.timezone.utc).timestamp()),))
            messages_to_send = cursor.fetchall()

            for msg_id, user_id, channel_id, message_content, send_at in messages_to_send:
                channel = self.bot.get_channel(channel_id)
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
            target_time = dateparser.parse(send_at, settings={'TIMEZONE': timezone, 'RETURN_AS_TIMEZONE_AWARE': True}).time()
        except Exception as e:
            await interaction.followup.send(f'An error occurred: {e}')
            return
      
        if target_time is None:
            await interaction.followup.send("Sorry, I couldn't understand the time you provided. Please make sure to use a valid format.")
            return
        elif not isinstance(interaction.channel, discord.TextChannel):
            await interaction.followup.send("This command can only be used in a text channel.")
            return

        recurring_task = self._create_recurring_message_task(
            channel=interaction.channel,
            message=message,
            user_name=interaction.user.display_name,
            target_time=target_time,
        )
        self.recurring_tasks.append(recurring_task)

        await interaction.followup.send(f"I will send the following recurring message every day at {target_time} {timezone}:\n\n{message}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MessageScheduler(bot))