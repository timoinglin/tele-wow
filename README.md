# TeleWoW MoP Controller

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version 1.0.0">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License: MIT">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white" alt="Platform: Windows">
  <img src="https://img.shields.io/badge/python--telegram--bot-20.8%2B-26A5E4?logo=telegram&logoColor=white" alt="python-telegram-bot 20.8+">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs welcome">
</p>

TeleWoW is a Windows-first Python Telegram bot for monitoring and controlling a local EmuCoach or TrinityCore Mists of Pandaria repack.

Clone this repository into the repack root directory. The repository folder must be named `tele-wow` and must sit next to `Repack` and `Database`. Relative paths in `.env` are resolved from the `tele-wow` folder, so the default paths intentionally use `../Repack` and `../Database`.

> 💛 **Running TeleWoW on your repack?** It's free and open-source, built and maintained in spare time. If it's saved you time monitoring your server — or you'd like to see it keep growing — a coffee genuinely helps. See [Support the Project](#support-the-project).
>
> [![Support the project on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/kneuma)


## Table of contents

- [Features](#features)
- [Preview](#preview)
- [Project layout](#project-layout)
- [Requirements](#requirements)
- [Easy install](#easy-install)
- [Manual setup](#manual-setup)
- [Running the bot](#running-the-bot)
- [Buttons](#buttons)
- [Remote Access setup](#remote-access-setup)
- [Auto-restart on crash](#auto-restart-on-crash)
- [Operational notes](#operational-notes)
- [Support the Project](#support-the-project)
- [License](#license)

## Features

- Telegram bot with inline keyboard control panel
- User ID whitelist protection
- `.env`-driven configuration
- Host stats for CPU, RAM, and disk usage
- Process monitoring for `mysqld.exe`, `authserver.exe`, and `worldserver.exe`
- Crash alerts with one-tap `▶ Start`, `🔄 Restart`, and `🎮 Open Status` buttons
- Optional `AUTO_RESTART_ON_CRASH` that recovers a crashed service plus its downstream dependents
- Per-service drill-down panel with PID, CPU%, RAM, uptime, and `☠ Force Stop`
- Start, stop, restart, force-stop, and `🔁 Restart All` actions
- Remote Access actions for worldserver commands
- `🔁 Graceful Restart` wizard: announce → 60s warning → save all → shutdown, with cancel
- In-bot account creation through worldserver RA commands
- Confirmation dialogs for risky actions
- Cleaner dashboard-style main panel with reduced bot message clutter

## Preview
Main dashboard

![Main dashboard](screenshots/1_main_dashboard.jpg)

Server status

![Server status](screenshots/2_server_status.jpg)

Remote Access

![Remote actions](screenshots/3_remote_actions.jpg)

Crash alert example

![Crash detected alert](screenshots/4_crash_detected.jpg)

## Project layout

```text
tele-wow/
   bot.py
   config.py
   database.py
   install_bot.bat
   LICENSE
   monitor.py
   ra.py
   requirements.txt
   start_bot.bat
   .env.example
   screenshots/
   TELEGRAM_SETUP.md
```

## Requirements

- Windows host
- Python 3.11+
- A Telegram bot token from BotFather
- One or more Telegram numeric user IDs for the whitelist
- A WoW repack root folder containing `Database` and `Repack`

## Easy install

Recommended for most users:

```bat
install_bot.bat
```

What the installer does:

- Explains that it only installs the bot, not the WoW repack itself
- Checks that `tele-wow` is placed beside `Database` and `Repack`
- Checks for Python 3.11+ and installs it with `winget` if needed
- Creates `.venv`
- Activates `.venv`
- Installs the required Python packages
- Creates `.env` from `.env.example` if `.env` does not already exist

What you still need to do after the installer finishes:

1. Open [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) and create your Telegram bot.
2. Edit `.env` and fill in your Telegram values.
3. Review the default `../Repack` and `../Database` paths in `.env`.
4. Enable RA in `Repack\worldserver.conf` if you want Remote Access features.
5. Start the bot with `start_bot.bat`.

The installer does not overwrite an existing `.env`, and it reuses an existing `.venv` if one is already present.

## Manual setup

1. Clone this repository into your repack root folder and make sure your structure looks like this:

   ```text
   Database/
   Repack/
   tele-wow/
   ```

2. Open a terminal inside the `tele-wow` folder.
3. Create and activate a virtual environment on Windows:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

4. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env`.
6. Keep the `tele-wow` folder in the repack root directory so the default `../Repack` and `../Database` paths stay valid.
7. Follow the Telegram setup guide in [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) to create your bot, get the token, and find your Telegram user IDs and chat ID.
8. Fill in these values in `.env`:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_ALLOWED_USER_IDS`
   - `TELEGRAM_ALERT_CHAT_ID`
   - Server executable and working-directory paths if your installation differs
   - `RA_HOST`, `RA_PORT`, `RA_USERNAME`, `RA_PASSWORD`, and `RA_TIMEOUT_SECONDS` if you want Remote Access features
   - Database connection settings if they differ from the default repack config

The default `.env.example` uses repo-relative paths such as `../Repack/worldserver.exe` and `../Database/_Server/MySQL.bat`, so it stays portable across different install locations.

## Running the bot

```powershell
python bot.py
```

Windows launcher:

```bat
start_bot.bat
```

The bot polls Telegram, schedules a 15-second heartbeat, and sends crash alerts to the configured chat ID.

`start_bot.bat` changes to the repo folder, activates `.venv`, and then runs `python bot.py`. This makes it suitable for double-click launch or for Windows Task Scheduler.

Task Scheduler note:

- Point the task to `start_bot.bat` inside the `tele-wow` folder
- Set `Start in` to the `tele-wow` folder

First run flow:

1. Start the bot with `python bot.py`.
2. Open Telegram and search for the bot username you created in BotFather.
3. Open the bot chat and press `Start`.
4. Send `/whoami` to read your Telegram User ID and Chat ID.
5. Add that User ID to `TELEGRAM_ALLOWED_USER_IDS` in `.env`.
6. Add that Chat ID to `TELEGRAM_ALERT_CHAT_ID` if you want alerts in that chat.
7. Restart the bot.
8. Send `/start` or `/menu` to open the control panel and enable the fixed navigation keyboard.

Before the whitelist is configured, only `/whoami` and `/debugid` are expected to work.

The bot tries to keep one main control-panel message updated instead of sending a new panel message for every action.

After the first authorized `/start` or `/menu`, the bot also enables a fixed reply keyboard with safe shortcuts for `🏠 Menu`, `🎮 Status`, `📊 Stats`, and `🌐 Remote`.

## Buttons

Main panel (2x2 inline keyboard):

- `🎮 Server Status`: PID, uptime, and memory for MySQL, AuthServer, and WorldServer
- `📊 System Stats`: host CPU, RAM, disk, and uptime for the monitored path
- `⚡ Quick Actions`: per-service drill-down with Start, Stop, Restart, Force Stop, plus `🔁 Restart All`
- `🌐 Remote Access`: RA-backed worldserver commands (`ℹ Server Info`, `💾 Save All`, `📣 Announce`, `🛑 Shutdown`, `🔁 Graceful Restart`, `👤 Account Creator`)

Fixed reply-keyboard shortcuts (always visible):

- `🏠 Menu`: return to the main dashboard panel
- `🎮 Status`: open the server status panel
- `📊 Stats`: open the system stats panel
- `🌐 Remote`: open the Remote Access panel

Quick Actions per-service rows:

- Offline service: one-tap `▶ Start`
- Online service: opens a drill-down with PID, CPU%, RAM, uptime, plus `🛑 Stop`, `🔄 Restart`, `☠ Force Stop`

Slash commands:

- `/start`, `/menu`: open the main panel and enable the reply keyboard
- `/status`, `/stats`: jump straight to status or stats panels
- `/whoami`, `/debugid`: print your Telegram User ID and Chat ID
- `/help`: list commands and wizard tips

Crash alerts include one-tap `▶ Start`, `🔄 Restart`, and `🎮 Open Status` buttons.

Confirmation steps are required for stop, restart, force-stop, shutdown, restart-all, graceful-restart, and account-creation. Announce sends immediately without a confirmation step.

### Graceful Restart wizard

`🌐 Remote Access > 🔁 Graceful Restart` chains an announce, a 60-second final warning, a `saveall`, and a `server shutdown 0`. The wizard prompts for a delay (in seconds) and an announcement template — send `default` to use the values from `.env`. While running, the panel shows progress and offers `⛔ Cancel Restart`, which sends a "restart cancelled" announcement and removes the pending jobs.

Defaults are configured via:

```text
GRACEFUL_RESTART_DEFAULT_DELAY_SECONDS=300
GRACEFUL_RESTART_DEFAULT_TEMPLATE=Server restart in {minutes} minutes - please log out safely.
```

The `{minutes}` token is replaced with the rounded countdown.

## Remote Access setup

Remote Access (`RA`) is used for worldserver command execution such as announcements, account commands, and server commands.

The current basic process-control features do not require `RA`, but any remote worldserver command feature does.

### Requirements

- `RA` must be enabled in `Repack\worldserver.conf`
- `worldserver.exe` must be running
- You need an existing WoW account for `RA` login
- That account must have a high enough security level for `Ra.MinLevel`

### Required `worldserver.conf` settings

Check the `CONSOLE AND REMOTE ACCESS` section in `Repack\worldserver.conf`.

These settings matter:

```text
Ra.Enable = 1
Ra.IP = "127.0.0.1"
Ra.Port = 3443
Ra.MinLevel = 3
```

Notes:

- `Ra.Enable = 1` enables the remote console
- `Ra.IP = "127.0.0.1"` is recommended when the bot runs on the same machine as the server
- `Ra.MinLevel = 3` means the login account must have security level `3` or higher

### Create the first RA account

`RA` cannot be used until you already have a privileged account.

The first account is usually created from the local `worldserver` console window, not through `RA` itself.

Typical bootstrap flow:

1. Start `worldserver.exe`
2. Open the local worldserver console window
3. Create an account
4. Grant that account a GM or admin level high enough for `RA`
5. Use that account later for `RA` login

Typical commands are:

```text
account create myadmin mypassword
account set gmlevel myadmin 3 -1
```

Important:

- Command syntax can vary slightly between core versions
- If your core uses a different account permission command, use the equivalent command available in your console
- `-1` commonly means all realms on Trinity or SkyFire style cores

### How `RA` is used

Once `RA` is configured, it can be used for commands such as:

- server announcements
- save commands
- shutdown commands
- account creation commands handled by worldserver

### RA values in `.env`

Add these values to `.env`:

```text
RA_HOST=127.0.0.1
RA_PORT=3443
RA_USERNAME=your-ra-account
RA_PASSWORD=your-ra-password
RA_TIMEOUT_SECONDS=10
```

### Using RA in the bot

After the RA values are saved in `.env`:

1. Restart the bot
2. Open the Telegram control panel with `/start` or `/menu`
3. Open `🌐 Remote Access`
4. Use one of the built-in actions:
   - `ℹ Server Info`
   - `💾 Save All`
   - `📣 Announce`
   - `🛑 Shutdown`
   - `🔁 Graceful Restart`
   - `👤 Account Creator`

For actions that need extra input, the bot will ask you to reply in chat.

Examples:

- `📣 Announce`: send the announcement text in chat (no confirmation step — broadcasts immediately)
- `🛑 Shutdown`: send the shutdown delay in seconds, then confirm
- `🔁 Graceful Restart`: send the delay in seconds (or `default`), then the announcement template (or `default`), then confirm

You can send `cancel` during an input step to stop the current action.

### Using Account Creator

1. Open the Telegram control panel
2. Press `👤 Account Creator`
3. Press `➕ Create Account`
4. Send the new username in chat
5. Send the new password in chat
6. Confirm the action when the bot asks

The bot will call the worldserver account creation command through `RA`.

Note: your username and password messages remain in your Telegram chat history. Long-press them and delete after creation if you do not want them to persist.

`RA` is not used to start or stop Windows processes like `mysqld.exe`, `authserver.exe`, or `worldserver.exe`. Those actions stay in the local process-control layer.

## Auto-restart on crash

Set `AUTO_RESTART_ON_CRASH=true` in `.env` to make the bot recover crashed services automatically. It accepts `true/false` (also `1/0`, `yes/no`, `on/off`) and defaults to `false`.

When enabled, the bot restarts a down service **and everything downstream of it**, in dependency order. This includes a service that is **already down when the bot starts** — it does not need to witness the crash:

| Down service | Restarted |
|--------------|-----------|
| `mysql`      | MySQL, AuthServer, WorldServer |
| `auth`       | AuthServer, WorldServer |
| `world`      | WorldServer |

The crash alert changes to `⚠️ CRASH DETECTED — trying to restart`, then updates in place to `✅ Auto-restart complete` or a failure notice with the per-step log. The bot retries a service up to 3 times; after that it posts `❌ Auto-restart failed after 3 attempts — manual action needed` and stays quiet for that service until it is healthy again, so a permanently broken service cannot spam the chat. Manual `▶ Start` / `🔄 Restart` / `🎮 Open Status` buttons remain on the message.

When `AUTO_RESTART_ON_CRASH=false` the original behaviour applies: one crash alert per service with manual recovery buttons and no automatic action.

## Operational notes

- MySQL is launched through `Database\_Server\MySQL.bat` by default to match the existing repack tooling.
- AuthServer and WorldServer are launched from the `Repack` folder because their config and data directories are relative.
- Restarting MySQL also restarts dependent server processes in dependency order.
- `AUTO_RESTART_ON_CRASH` recovers a crashed service plus its downstream dependents; see [Auto-restart on crash](#auto-restart-on-crash).
- Unauthorized Telegram users are ignored unless their numeric ID appears in the whitelist.
- Remote console features require RA to be enabled in `Repack\worldserver.conf` by setting `Ra.Enable = 1` in the `CONSOLE AND REMOTE ACCESS` section.

## Support the Project

This project is free and open-source, built and maintained in spare time. If it's saved you time setting up or running your server — or you'd just like to see it keep growing — a coffee is hugely appreciated and helps keep the WoW repack tools maintained and improving.

[![Support the project on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/kneuma)

Every contribution also funds more free tools for the MoP / Cata repack community — thank you! 💛

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
