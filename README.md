# Event Helper Bot

A Discord bot for managing event channels, scheduling messages, and assigning roles through reactions.

## Features

- Create an event role, category, and standard event channels.
- Schedule one-time messages using natural-language dates and times.
- Schedule, list, and cancel daily messages.
- Set a personal timezone for scheduled messages.
- Create reaction-based role assignment messages and update them later.
- Persist schedules, timezone settings, and role mappings in SQLite.

## Requirements

- Python 3.9 or newer
- A Discord application and bot token
- A Discord server ID
- A server with the `Event IT` and `Bot` roles

## Setup

1. Clone the repository and enter the project directory.
2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell, activate it with:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root:

   ```env
   DISCORD_TOKEN=your-bot-token
   GUILD_ID=123456789012345678
   ```

5. Invite the bot to the server with the permissions required for its commands. At minimum it needs to be able to manage roles, create and manage channels, send messages, embed links, add reactions, and manage messages. Enable the **Server Members Intent**, **Message Content Intent**, and **Reaction Intent** in the Discord Developer Portal.

6. Start the bot:

   ```bash
   python main.py
   ```

The bot creates `database.db` automatically on first startup. Slash commands are synchronized to the guild configured by `GUILD_ID`.

## Commands

| Command | Access | Description |
| --- | --- | --- |
| `/create_event event_name` | Administrator | Creates an event role, category, and text, voice, and forum channels. |
| `/schedule_message_at message send_at` | Any member | Sends a one-time message at a future date and time. |
| `/daily_message_at message send_at` | `Event IT` or `Bot` role | Sends a message every day at the selected time. |
| `/list_daily_messages` | `Event IT` or `Bot` role | Lists daily messages scheduled in the current channel. |
| `/cancel_daily_message daily_id` | `Event IT` or `Bot` role | Cancels a daily message in the current channel. |
| `/set_timezone timezone` | Any member | Sets the timezone used when interpreting scheduled times. |
| `/post_role_message emoji role_name` | Administrator | Posts a reaction message that assigns a role. |
| `/edit_role_message message_id emoji role_name` | Administrator | Adds, updates, or removes a role assignment on an existing role message. |

## Scheduling notes

- Without a saved timezone, scheduling uses `UTC`.
- `send_at` accepts natural-language input such as `tomorrow at 3pm` or `2026-12-01 18:30`.
- One-time messages are checked every 30 seconds.
- Daily message IDs are returned when created and are required for cancellation.
- The bot stores scheduled timestamps in UTC while displaying or interpreting them using the user's timezone.

## Project layout

```text
main.py                    Bot startup and guild command synchronization
database.py                SQLite schema initialization
cogs/event_creator.py      Event role, category, and channel creation
cogs/message_scheduler.py  One-time and daily message scheduling
cogs/role_assigner.py      Reaction-based role assignment
cogs/user_settings.py      Per-user timezone settings
requirements.txt           Python dependencies
```

## Development

The bot is intended to run as a single process with its SQLite database in the project directory. Keep `.env`, `database.db`, and Python cache files out of version control; the included `.gitignore` already covers them.

## Troubleshooting

- If slash commands do not appear, confirm `GUILD_ID` is correct and restart the bot so it can synchronize commands.
- If reactions do not assign roles, confirm the bot can manage the target role and that its highest role is above the role it must assign.
- If event creation fails, verify the bot can manage roles and create/manage the required channel types.
- If scheduled messages fail after a restart, verify that the bot can access the target channel and that the required intents and permissions are enabled.