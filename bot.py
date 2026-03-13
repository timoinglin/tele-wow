from __future__ import annotations

import asyncio
from datetime import datetime
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import AppConfig, load_config
from database import DatabaseClient
from monitor import ProcessMonitor, ServerController
from ra import RemoteAccessClient, RemoteAccessError


LOGGER = logging.getLogger(__name__)

NAVIGATION_MENU_LABEL = "🏠 Menu"
NAVIGATION_STATUS_LABEL = "🎮 Status"
NAVIGATION_STATS_LABEL = "📊 Stats"
NAVIGATION_REMOTE_LABEL = "🌐 Remote"


def build_navigation_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [NAVIGATION_MENU_LABEL, NAVIGATION_STATUS_LABEL],
            [NAVIGATION_STATS_LABEL, NAVIGATION_REMOTE_LABEL],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choose a panel shortcut...",
    )


def build_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📊 System Stats", callback_data="menu:stats"),
                InlineKeyboardButton("🎮 Server Status", callback_data="menu:status"),
            ],
            [
                InlineKeyboardButton("⚡ Quick Actions", callback_data="menu:quick"),
                InlineKeyboardButton("🌐 Remote Access", callback_data="menu:remote"),
            ],
            [InlineKeyboardButton("👤 Account Creator", callback_data="menu:account")],
        ]
    )


def build_stats_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data="menu:stats")],
            [
                InlineKeyboardButton("🎮 Status", callback_data="menu:status"),
                InlineKeyboardButton("⬅ Main", callback_data="menu:main"),
            ],
        ]
    )


def build_status_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔄 Refresh Status", callback_data="menu:status")],
            [
                InlineKeyboardButton("⚡ Quick Actions", callback_data="menu:quick"),
                InlineKeyboardButton("⬅ Main", callback_data="menu:main"),
            ],
        ]
    )


def build_quick_actions_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("▶ MySQL", callback_data="action:start:mysql"),
                InlineKeyboardButton("🛑 MySQL", callback_data="confirm:service:stop:mysql"),
                InlineKeyboardButton("🔄 MySQL", callback_data="confirm:service:restart:mysql"),
            ],
            [
                InlineKeyboardButton("▶ Auth", callback_data="action:start:auth"),
                InlineKeyboardButton("🛑 Auth", callback_data="confirm:service:stop:auth"),
                InlineKeyboardButton("🔄 Auth", callback_data="confirm:service:restart:auth"),
            ],
            [
                InlineKeyboardButton("▶ World", callback_data="action:start:world"),
                InlineKeyboardButton("🛑 World", callback_data="confirm:service:stop:world"),
                InlineKeyboardButton("🔄 World", callback_data="confirm:service:restart:world"),
            ],
            [
                InlineKeyboardButton("🎮 Status", callback_data="menu:status"),
                InlineKeyboardButton("⬅ Main", callback_data="menu:main"),
            ],
        ]
    )


def build_remote_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("ℹ Server Info", callback_data="ra:server_info"),
                InlineKeyboardButton("💾 Save All", callback_data="ra:saveall"),
            ],
            [
                InlineKeyboardButton("📣 Announce", callback_data="ra:announce"),
                InlineKeyboardButton("🛑 Shutdown", callback_data="ra:shutdown"),
            ],
            [
                InlineKeyboardButton("👤 Account Creator", callback_data="menu:account"),
                InlineKeyboardButton("⬅ Main", callback_data="menu:main"),
            ],
        ]
    )


def build_account_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Create Account", callback_data="ra:account_create")],
            [
                InlineKeyboardButton("🌐 Remote Access", callback_data="menu:remote"),
                InlineKeyboardButton("⬅ Main", callback_data="menu:main"),
            ],
        ]
    )


def build_confirm_menu(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=confirm_data),
                InlineKeyboardButton("⬅ Cancel", callback_data=cancel_data),
            ]
        ]
    )


def is_authorized(update: Update, config: AppConfig) -> bool:
    user = update.effective_user
    return user is not None and user.id in config.allowed_user_ids


def get_controller(context: ContextTypes.DEFAULT_TYPE) -> ServerController:
    return context.application.bot_data["controller"]


def get_monitor(context: ContextTypes.DEFAULT_TYPE) -> ProcessMonitor:
    return context.application.bot_data["monitor"]


def get_database(context: ContextTypes.DEFAULT_TYPE) -> DatabaseClient:
    return context.application.bot_data["database"]


def get_remote_access(context: ContextTypes.DEFAULT_TYPE) -> RemoteAccessClient:
    return context.application.bot_data["remote_access"]


def remember_panel_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int) -> None:
    context.user_data["panel_chat_id"] = chat_id
    context.user_data["panel_message_id"] = message_id


async def ensure_navigation_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return

    if context.user_data.get("navigation_keyboard_enabled"):
        return

    await message.reply_text(
        "Navigation keyboard enabled. Use these fixed buttons to jump between safe panels.",
        reply_markup=build_navigation_keyboard(),
    )
    context.user_data["navigation_keyboard_enabled"] = True


async def render_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    chat_id = context.user_data.get("panel_chat_id")
    message_id = context.user_data.get("panel_message_id")

    if chat_id and message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return
        except BadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return
            context.user_data.pop("panel_chat_id", None)
            context.user_data.pop("panel_message_id", None)
        except TelegramError:
            context.user_data.pop("panel_chat_id", None)
            context.user_data.pop("panel_message_id", None)

    message = update.effective_message
    if message is None:
        return

    sent_message = await message.reply_text(text, reply_markup=reply_markup)
    remember_panel_message(context, sent_message.chat_id, sent_message.message_id)


async def whoami_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return

    user = update.effective_user
    chat = update.effective_chat

    if user is None:
        await update.effective_message.reply_text("Unable to determine the Telegram user for this update.")
        return

    chat_id = "unknown" if chat is None else str(chat.id)
    username = "unknown" if user.username is None else f"@{user.username}"
    full_name = user.full_name or "unknown"

    await update.effective_message.reply_text(
        "TeleWoW identity info\n"
        f"User ID: {user.id}\n"
        f"Chat ID: {chat_id}\n"
        f"Username: {username}\n"
        f"Name: {full_name}\n\n"
        "Add the User ID to TELEGRAM_ALLOWED_USER_IDS.\n"
        "For a private chat, Chat ID is usually the correct TELEGRAM_ALERT_CHAT_ID."
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: AppConfig = context.application.bot_data["config"]
    if not is_authorized(update, config):
        return

    await ensure_navigation_keyboard(update, context)
    text = await build_main_text(context)
    await render_panel(update, context, text, build_main_menu())


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: AppConfig = context.application.bot_data["config"]
    if not is_authorized(update, config):
        return

    await ensure_navigation_keyboard(update, context)
    controller = get_controller(context)
    stats = await asyncio.to_thread(controller.get_system_stats)
    await render_panel(update, context, format_stats(stats), build_stats_menu())


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: AppConfig = context.application.bot_data["config"]
    if not is_authorized(update, config):
        return

    await ensure_navigation_keyboard(update, context)
    statuses, database_online, ra_online = await get_status_snapshot(context)
    await render_panel(update, context, format_statuses(statuses, database_online, ra_online), build_status_menu())


async def show_remote_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await render_panel(update, context, build_remote_text(), build_remote_menu())


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: AppConfig = context.application.bot_data["config"]
    if not is_authorized(update, config):
        return

    message = update.effective_message
    if message is None or message.text is None:
        return

    pending_action = context.user_data.get("pending_action")
    if not pending_action:
        if message.text == NAVIGATION_MENU_LABEL:
            text = await build_main_text(context)
            await render_panel(update, context, text, build_main_menu())
            return
        if message.text == NAVIGATION_STATUS_LABEL:
            statuses, database_online, ra_online = await get_status_snapshot(context)
            await render_panel(update, context, format_statuses(statuses, database_online, ra_online), build_status_menu())
            return
        if message.text == NAVIGATION_STATS_LABEL:
            controller = get_controller(context)
            stats = await asyncio.to_thread(controller.get_system_stats)
            await render_panel(update, context, format_stats(stats), build_stats_menu())
            return
        if message.text == NAVIGATION_REMOTE_LABEL:
            await show_remote_panel(update, context)
            return

    if not pending_action:
        return

    text = message.text.strip()
    if text.lower() == "cancel":
        context.user_data.pop("pending_action", None)
        text = await build_main_text(context)
        await render_panel(update, context, text, build_main_menu())
        return

    action_type = pending_action.get("type")
    if action_type == "announce_text":
        context.user_data["pending_action"] = {"type": "announce_confirm", "text": text}
        await render_panel(
            update,
            context,
            f"📣 Confirm Announce\n\n{text}",
            build_confirm_menu("execute:ra:announce", "menu:remote"),
        )
        return

    if action_type == "shutdown_delay":
        try:
            delay = int(text)
        except ValueError:
            await render_panel(
                update,
                context,
                "Send the shutdown delay in seconds, or send cancel.",
                build_remote_menu(),
            )
            return

        context.user_data["pending_action"] = {"type": "shutdown_confirm", "delay": delay}
        await render_panel(
            update,
            context,
            f"🛑 Confirm Shutdown\n\nShutdown the server in {delay} seconds?",
            build_confirm_menu(f"execute:ra:shutdown:{delay}", "menu:remote"),
        )
        return

    if action_type == "account_username":
        if " " in text:
            await render_panel(
                update,
                context,
                "Username cannot contain spaces. Send a username or send cancel.",
                build_account_menu(),
            )
            return
        context.user_data["pending_action"] = {"type": "account_password", "username": text}
        await render_panel(
            update,
            context,
            f"Username saved: {text}\nNow send the password for the new account, or send cancel.",
            build_account_menu(),
        )
        return

    if action_type == "account_password":
        username = pending_action.get("username")
        if not username:
            context.user_data.pop("pending_action", None)
            await render_panel(update, context, "Account creation state was lost. Start again.", build_account_menu())
            return
        if " " in text:
            await render_panel(
                update,
                context,
                "Password cannot contain spaces. Send a password or send cancel.",
                build_account_menu(),
            )
            return

        context.user_data["pending_action"] = {
            "type": "account_confirm",
            "username": username,
            "password": text,
        }
        await render_panel(
            update,
            context,
            f"👤 Confirm Account Creation\n\nCreate account: {username}\nPassword: hidden",
            build_confirm_menu("execute:ra:account_create", "menu:account"),
        )
        return


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: AppConfig = context.application.bot_data["config"]
    if not is_authorized(update, config):
        if update.callback_query is not None:
            await update.callback_query.answer()
        return

    query = update.callback_query
    if query is None or query.data is None:
        return

    await query.answer()
    remember_panel_message(context, query.message.chat_id, query.message.message_id)

    if query.data == "menu:main":
        context.user_data.pop("pending_action", None)
        text = await build_main_text(context)
        await query.edit_message_text(text, reply_markup=build_main_menu())
        return

    if query.data == "menu:quick":
        context.user_data.pop("pending_action", None)
        await query.edit_message_text(build_quick_actions_text(), reply_markup=build_quick_actions_menu())
        return

    if query.data == "menu:remote":
        context.user_data.pop("pending_action", None)
        await query.edit_message_text(build_remote_text(), reply_markup=build_remote_menu())
        return

    if query.data == "menu:stats":
        context.user_data.pop("pending_action", None)
        controller = get_controller(context)
        stats = await asyncio.to_thread(controller.get_system_stats)
        await query.edit_message_text(format_stats(stats), reply_markup=build_stats_menu())
        return

    if query.data == "menu:status":
        context.user_data.pop("pending_action", None)
        statuses, database_online, ra_online = await get_status_snapshot(context)
        await query.edit_message_text(
            format_statuses(statuses, database_online, ra_online),
            reply_markup=build_status_menu(),
        )
        return

    if query.data == "menu:account":
        context.user_data.pop("pending_action", None)
        text = (
            "👤 Account Creator\n\n"
            "Create a new WoW account through Remote Access.\n"
            "Press Create Account and then reply with the username and password in chat.\n"
            "You will get a confirmation step before the command is sent.\n"
            "Send cancel at any prompt to stop."
        )
        await query.edit_message_text(text, reply_markup=build_account_menu())
        return

    if query.data == "ra:server_info":
        result = await run_ra_command(context, "server info")
        await query.edit_message_text(format_ra_result("Server Info", result), reply_markup=build_remote_menu())
        return

    if query.data == "ra:saveall":
        result = await run_ra_command(context, "saveall")
        await query.edit_message_text(format_ra_result("Save All", result), reply_markup=build_remote_menu())
        return

    if query.data == "ra:announce":
        context.user_data["pending_action"] = {"type": "announce_text"}
        await query.edit_message_text(
            "📣 Announce\n\nSend the announcement text in chat, or send cancel.",
            reply_markup=build_remote_menu(),
        )
        return

    if query.data == "ra:shutdown":
        context.user_data["pending_action"] = {"type": "shutdown_delay"}
        await query.edit_message_text(
            "🛑 Shutdown\n\nSend the shutdown delay in seconds, or send cancel.",
            reply_markup=build_remote_menu(),
        )
        return

    if query.data == "ra:account_create":
        context.user_data["pending_action"] = {"type": "account_username"}
        await query.edit_message_text(
            "👤 Account Creator\n\nSend the new account username in chat, or send cancel.",
            reply_markup=build_account_menu(),
        )
        return

    if query.data.startswith("confirm:service:"):
        _, _, action, service_key = query.data.split(":", 3)
        text = format_service_confirmation(action, service_key)
        await query.edit_message_text(
            text,
            reply_markup=build_confirm_menu(
                f"execute:service:{action}:{service_key}",
                "menu:quick",
            ),
        )
        return

    if query.data == "execute:ra:announce":
        pending_action = context.user_data.pop("pending_action", {})
        announce_text = pending_action.get("text", "")
        result = await run_ra_command(context, f"announce {announce_text}")
        await query.edit_message_text(format_ra_result("Announce", result), reply_markup=build_remote_menu())
        return

    if query.data.startswith("execute:ra:shutdown:"):
        context.user_data.pop("pending_action", None)
        delay = query.data.rsplit(":", 1)[1]
        result = await run_ra_command(context, f"server shutdown {delay}")
        await query.edit_message_text(format_ra_result("Shutdown", result), reply_markup=build_remote_menu())
        return

    if query.data == "execute:ra:account_create":
        pending_action = context.user_data.pop("pending_action", {})
        username = pending_action.get("username")
        password = pending_action.get("password")
        if not username or not password:
            await query.edit_message_text("Account creation state was lost. Start again.", reply_markup=build_account_menu())
            return
        result = await run_ra_command(context, f"account create {username} {password}")
        await query.edit_message_text(format_ra_result("Account Create", result), reply_markup=build_account_menu())
        return

    if query.data.startswith("execute:service:"):
        _, _, action, service_key = query.data.split(":", 3)
        controller = get_controller(context)
        result_lines = await asyncio.to_thread(run_service_action, controller, action, service_key)
        text = format_action_result(action, service_key, result_lines)
        await query.edit_message_text(text, reply_markup=build_quick_actions_menu())
        return

    if query.data.startswith("action:"):
        _, action, service_key = query.data.split(":", 2)
        controller = get_controller(context)
        result_lines = await asyncio.to_thread(run_service_action, controller, action, service_key)
        text = format_action_result(action, service_key, result_lines)
        await query.edit_message_text(text, reply_markup=build_quick_actions_menu())
        return

    await query.edit_message_text("Unknown action.", reply_markup=build_main_menu())


def run_service_action(controller: ServerController, action: str, service_key: str) -> list[str]:
    if action == "start":
        return controller.start_service(service_key)
    if action == "restart":
        return controller.restart_service(service_key)
    if action == "stop":
        return controller.stop_service(service_key)
    raise ValueError(f"Unsupported action: {action}")


async def heartbeat(context: ContextTypes.DEFAULT_TYPE) -> None:
    monitor = get_monitor(context)
    crashed_services = await asyncio.to_thread(monitor.detect_crashes)

    if not crashed_services:
        return

    config: AppConfig = context.application.bot_data["config"]
    for service in crashed_services:
        await context.bot.send_message(
            chat_id=config.alert_chat_id,
            text=(
                "⚠️ CRASH DETECTED\n"
                f"Service: {service.display_name}\n"
                f"Process: {config.services[service.key].process_name}"
            ),
        )


async def error_handler(_: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.exception("Unhandled Telegram error", exc_info=context.error)


async def get_status_snapshot(context: ContextTypes.DEFAULT_TYPE) -> tuple[dict[str, object], bool, bool]:
    controller = get_controller(context)
    database = get_database(context)
    remote_access = get_remote_access(context)
    statuses, database_online, ra_online = await asyncio.gather(
        asyncio.to_thread(controller.get_service_statuses),
        asyncio.to_thread(database.ping),
        asyncio.to_thread(remote_access.ping),
    )
    return statuses, database_online, ra_online


async def run_ra_command(context: ContextTypes.DEFAULT_TYPE, command: str) -> str:
    remote_access = get_remote_access(context)
    try:
        result = await asyncio.to_thread(remote_access.run_command, command)
        return result.output or "Command completed with no output."
    except RemoteAccessError as exc:
        return f"RA error: {exc}"
    except OSError as exc:
        return f"Connection error: {exc}"


async def build_main_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    config: AppConfig = context.application.bot_data["config"]
    controller = get_controller(context)
    (statuses, database_online, ra_online), stats = await asyncio.gather(
        get_status_snapshot(context),
        asyncio.to_thread(controller.get_system_stats),
    )
    running_count = sum(1 for status in statuses.values() if status.running)

    return (
        "TeleWoW Control Panel\n"
        f"Services online: {running_count}/3\n"
        f"DB: {format_health(database_online)} | RA: {format_health(ra_online)}\n"
        f"CPU: {stats['cpu_percent']}% | RAM: {stats['memory_percent']}% | Disk: {stats['disk_percent']}%\n"
        f"Allowed users: {len(config.allowed_user_ids)} | Heartbeat: {config.poll_interval_seconds}s\n\n"
        f"MySQL {format_status_chip(statuses['mysql'].running)} | "
        f"Auth {format_status_chip(statuses['auth'].running)} | "
        f"World {format_status_chip(statuses['world'].running)}\n\n"
        "Use the buttons below to open a panel or run an action."
    )


def format_health(is_online: bool) -> str:
    return "online" if is_online else "offline"


def format_status_chip(is_online: bool) -> str:
    return "🟢" if is_online else "🔴"


def build_quick_actions_text() -> str:
    return (
        "Quick Actions\n"
        "Use ▶ to start, 🛑 to stop, and 🔄 to restart a service.\n"
        "Starting World will automatically ensure MySQL and Auth are running first."
    )


def build_remote_text() -> str:
    return (
        "🌐 Remote Access\n"
        "Use RA-backed worldserver commands from here.\n"
        "Available actions: server info, saveall, announce, shutdown, and account creation."
    )


def format_stats(stats: dict[str, float | str]) -> str:
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uptime = format_duration_from_seconds(max(0, int(datetime.now().timestamp() - float(stats["boot_time"]))))
    return (
        "📊 System Stats\n"
        f"Updated: {updated_at}\n\n"
        f"CPU load: {stats['cpu_percent']}%\n"
        f"CPU cores: {stats['cpu_count_physical']} physical / {stats['cpu_count_logical']} logical\n"
        f"RAM: {stats['memory_used_gb']} GB / {stats['memory_total_gb']} GB used ({stats['memory_percent']}%)\n"
        f"RAM free: {stats['memory_available_gb']} GB\n"
        f"Disk: {stats['disk_used_gb']} GB / {stats['disk_total_gb']} GB used ({stats['disk_percent']}%)\n"
        f"Disk free: {stats['disk_free_gb']} GB\n"
        f"Host uptime: {uptime}\n"
        f"Monitored path: {stats['disk_path']}"
    )


def format_statuses(statuses: dict[str, object], database_online: bool, ra_online: bool) -> str:
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    running_count = sum(1 for status in statuses.values() if status.running)
    lines = [
        "🎮 Server Status",
        f"Updated: {updated_at}",
        f"Services online: {running_count}/3",
        f"Database login check: {'online' if database_online else 'offline'}",
        f"RA login check: {'online' if ra_online else 'offline'}",
        "",
    ]
    for key in ("mysql", "auth", "world"):
        status = statuses[key]
        if status.running:
            uptime = format_duration_from_timestamp(status.started_at)
            memory = "unknown" if status.memory_mb is None else f"{status.memory_mb} MB"
            lines.append(f"🟢 {status.display_name}")
            lines.append(f"PID: {status.pid}")
            lines.append(f"Uptime: {uptime}")
            lines.append(f"Memory: {memory}")
        else:
            lines.append(f"🔴 {status.display_name}")
            lines.append("Status: offline")
        lines.append("")
    return "\n".join(lines)


def format_action_result(action: str, service_key: str, result_lines: list[str]) -> str:
    verb = {
        "start": "Start",
        "stop": "Stop",
        "restart": "Restart",
    }.get(action, action.title())
    service_name = {
        "mysql": "MySQL",
        "auth": "AuthServer",
        "world": "WorldServer",
    }.get(service_key, service_key)
    return f"⚡ {verb} {service_name}\n\n" + "\n".join(f"• {line}" for line in result_lines)


def format_service_confirmation(action: str, service_key: str) -> str:
    verb = {
        "stop": "stop",
        "restart": "restart",
    }.get(action, action)
    service_name = {
        "mysql": "MySQL",
        "auth": "AuthServer",
        "world": "WorldServer",
    }.get(service_key, service_key)
    return f"⚠ Confirm {verb.title()}\n\nDo you want to {verb} {service_name}?"


def format_ra_result(title: str, output: str) -> str:
    return f"🌐 {title}\n\n{output}".strip()


def format_duration_from_timestamp(started_at: float | None) -> str:
    if started_at is None:
        return "unknown"
    return format_duration_from_seconds(max(0, int(datetime.now().timestamp() - started_at)))


def format_duration_from_seconds(total_seconds: int) -> str:
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def build_application(config: AppConfig) -> Application:
    monitor = ProcessMonitor(config)
    monitor.seed_state()
    controller = ServerController(config, monitor=monitor)
    database = DatabaseClient(config.database)
    remote_access = RemoteAccessClient(config.remote_access)

    application = ApplicationBuilder().token(config.bot_token).build()
    application.bot_data.update(
        {
            "config": config,
            "monitor": monitor,
            "controller": controller,
            "database": database,
            "remote_access": remote_access,
        }
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", start_command))
    application.add_handler(CommandHandler("whoami", whoami_command))
    application.add_handler(CommandHandler("debugid", whoami_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    application.add_handler(CallbackQueryHandler(callback_router))
    application.add_error_handler(error_handler)

    if application.job_queue is None:
        raise RuntimeError("python-telegram-bot job queue is unavailable. Install the job-queue extra.")

    application.job_queue.run_repeating(heartbeat, interval=config.poll_interval_seconds, first=0)
    return application


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )
    config = load_config()
    application = build_application(config)
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()