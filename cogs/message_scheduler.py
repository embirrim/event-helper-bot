'''
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

    '''