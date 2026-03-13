# Telegram Bot Setup

This guide covers the Telegram-specific setup for TeleWoW: creating a bot, getting the bot token, finding Telegram user IDs, and filling the related `.env` values.

## What you need

- A Telegram account
- Telegram installed on your phone or desktop
- The `tele-wow` project folder already placed in the repack root directory

## 1. Create the bot with BotFather

1. Open Telegram and search for `@BotFather`.
2. Start a chat with BotFather.
3. Send `/newbot`.
4. Enter a display name for the bot.
   Example: `TeleWoW Controller`
5. Enter a unique bot username ending with `bot`.
   Example: `telewow_mop_controller_bot`
6. BotFather will return a bot token.

You can find your bot later by searching Telegram for that username.

BotFather may also give you a direct link such as `https://t.me/your_bot_name`. Opening that link will take you straight to the bot chat.

The token looks similar to this:

```text
1234567890:AAExampleTokenValueReplaceThis
```

Copy this token and place it in `.env` as:

```text
TELEGRAM_BOT_TOKEN=1234567890:AAExampleTokenValueReplaceThis
```

## 2. Find Telegram user IDs

TeleWoW uses a whitelist and ignores all commands from users whose numeric Telegram user ID is not listed in the configuration.

### Option A: Use a Telegram helper bot

1. Search Telegram for `@userinfobot` or another ID lookup bot.
2. Start the bot.
3. Send any message.
4. Read your numeric Telegram user ID from the reply.

Set these values in `.env` if you want alerts sent to your private chat:

```text
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321
TELEGRAM_ALERT_CHAT_ID=123456789
```

### Option B: Read it from TeleWoW later

TeleWoW includes two setup-safe commands that work even before the whitelist is configured:

- `/whoami`
- `/debugid`

These commands only return the caller's own Telegram identity details and do not grant access to control features.

Use them like this:

1. Start TeleWoW from the `tele-wow` folder.
2. Search for your bot by its username in Telegram and open the private chat.
3. Press `Start` in that chat.
4. Send `/whoami`.
5. Add the reported `User ID` to `TELEGRAM_ALLOWED_USER_IDS`.
6. Copy the reported `Chat ID` into `TELEGRAM_ALERT_CHAT_ID` if you want private alerts.

At this point, `/whoami` and `/debugid` are the only commands that are expected to work before the whitelist is configured.

Use a comma-separated list when you want to allow more than one person:

```text
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321,555666777
```

## 3. Understand `TELEGRAM_ALERT_CHAT_ID`

This value controls where crash alerts are sent.

- For a private chat with yourself, `TELEGRAM_ALERT_CHAT_ID` is usually the same as your user ID.
- For a group, the chat ID is different from your user ID.
- For most personal setups, using your private chat ID is the simplest option.

## 4. Start a chat with your bot

Before TeleWoW can send messages to you, you must open your bot in Telegram and press `Start`.

If you skip this, Telegram may reject outgoing messages because the bot has no active chat with you yet.

If you cannot find the bot:

1. Search Telegram for the username you created in BotFather.
2. Make sure you open the bot chat itself, not the BotFather chat.
3. Press `Start` after opening the chat.

## 5. Fill the Telegram values in `.env`

Minimum Telegram-related configuration:

```text
TELEGRAM_BOT_TOKEN=1234567890:AAExampleTokenValueReplaceThis
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321
TELEGRAM_ALERT_CHAT_ID=123456789
POLL_INTERVAL_SECONDS=15
```

After saving `.env`, stop the bot if it is already running and start it again so the new values are loaded.

Then go back to the bot chat and send:

- `/start`
- `/menu`

That opens the main control panel with the inline buttons and enables the fixed reply-keyboard shortcuts for `🏠 Menu`, `🎮 Status`, `📊 Stats`, and `🌐 Remote`.

Quick rule:

- Before whitelist setup: `/whoami` and `/debugid` work
- After whitelist setup and bot restart: `/start` and `/menu` show the inline control panel and the fixed navigation keyboard

## 6. Recommended privacy settings

- Do not post the bot token in screenshots or chat logs.
- If the token is leaked, use BotFather `/revoke` or regenerate it immediately.
- Keep the bot private and do not add it to public groups unless that is intentional.
- Keep the user ID whitelist limited to people who should be able to control the server.

## 7. Quick verification checklist

1. Bot created in BotFather
2. Token copied into `.env`
3. One or more allowed Telegram user IDs added to `.env`, from `@userinfobot` or `/whoami`
4. Alert chat ID added to `.env`
5. You opened the bot chat and pressed `Start`
6. TeleWoW is launched from the `tele-wow` folder

## 8. Common problems

### The bot does not respond

- Check that `TELEGRAM_BOT_TOKEN` is correct.
- Confirm that you started the bot chat in Telegram.
- Confirm that your Telegram account is included in `TELEGRAM_ALLOWED_USER_IDS`.
- Try `/whoami` to confirm which User ID and Chat ID Telegram is sending.
- Restart the bot after editing `.env`.
- Send `/start` or `/menu` after the whitelist is configured.
- Check the console output for startup exceptions.

### `/whoami` works but `/start` does not show buttons

- Your Telegram user ID is probably not yet whitelisted.
- Copy the `User ID` shown by `/whoami` into `TELEGRAM_ALLOWED_USER_IDS`.
- Save `.env`.
- Restart the bot.
- Send `/start` again.

### Crash alerts are not delivered

- Confirm `TELEGRAM_ALERT_CHAT_ID` is correct.
- Confirm the bot already has permission to message that chat.
- If you are using a group, verify the correct group chat ID instead of your user ID.

### BotFather says the username is invalid

- The username must be unique.
- The username must end with `bot`.
- Try a longer or more specific name.