from __future__ import annotations

import asyncio
from datetime import datetime
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

from config import AppConfig, load_config
from database import DatabaseClient
from monitor import ProcessMonitor, ServerController


LOGGER = logging.getLogger(__name__)


def build_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📊 System Stats", callback_data="menu:stats"),
                InlineKeyboardButton("🎮 Server Status", callback_data="menu:status"),
            ],
            [InlineKeyboardButton("⚡ Quick Actions", callback_data="menu:quick")],
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
                InlineKeyboardButton("🔄 MySQL", callback_data="action:restart:mysql"),
            ],
            [
                InlineKeyboardButton("▶ Auth", callback_data="action:start:auth"),
                InlineKeyboardButton("🔄 Auth", callback_data="action:restart:auth"),
            ],
            [
                InlineKeyboardButton("▶ World", callback_data="action:start:world"),
                InlineKeyboardButton("🔄 World", callback_data="action:restart:world"),
            ],
            [
                InlineKeyboardButton("🎮 Status", callback_data="menu:status"),
                InlineKeyboardButton("⬅ Main", callback_data="menu:main"),
            ],
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

    await update.effective_message.reply_text(
        build_main_text(config),
        reply_markup=build_main_menu(),
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: AppConfig = context.application.bot_data["config"]
    if not is_authorized(update, config):
        return

    controller = get_controller(context)
    stats = await asyncio.to_thread(controller.get_system_stats)
    await update.effective_message.reply_text(format_stats(stats), reply_markup=build_stats_menu())


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: AppConfig = context.application.bot_data["config"]
    if not is_authorized(update, config):
        return

    statuses, database_online = await get_status_snapshot(context)
    await update.effective_message.reply_text(
        format_statuses(statuses, database_online),
        reply_markup=build_status_menu(),
    )


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

    if query.data == "menu:main":
        config = context.application.bot_data["config"]
        await query.edit_message_text(build_main_text(config), reply_markup=build_main_menu())
        return

    if query.data == "menu:quick":
        await query.edit_message_text(build_quick_actions_text(), reply_markup=build_quick_actions_menu())
        return

    if query.data == "menu:stats":
        controller = get_controller(context)
        stats = await asyncio.to_thread(controller.get_system_stats)
        await query.edit_message_text(format_stats(stats), reply_markup=build_stats_menu())
        return

    if query.data == "menu:status":
        statuses, database_online = await get_status_snapshot(context)
        await query.edit_message_text(format_statuses(statuses, database_online), reply_markup=build_status_menu())
        return

    if query.data == "menu:account":
        database = get_database(context)
        is_online = await asyncio.to_thread(database.ping)
        text = (
            "👤 Account Creator\n\n"
            "This panel is currently unavailable.\n"
            f"Database reachability: {'online' if is_online else 'offline'}."
        )
        await query.edit_message_text(text, reply_markup=build_main_menu())
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


async def get_status_snapshot(context: ContextTypes.DEFAULT_TYPE) -> tuple[dict[str, object], bool]:
    controller = get_controller(context)
    database = get_database(context)
    statuses, database_online = await asyncio.gather(
        asyncio.to_thread(controller.get_service_statuses),
        asyncio.to_thread(database.ping),
    )
    return statuses, database_online


def build_main_text(config: AppConfig) -> str:
    return (
        "TeleWoW Control Panel\n"
        f"Allowed users: {len(config.allowed_user_ids)}\n"
        f"Heartbeat: every {config.poll_interval_seconds} seconds\n\n"
        "Use the buttons below to view stats, inspect service status, or run quick actions."
    )


def build_quick_actions_text() -> str:
    return (
        "Quick Actions\n"
        "Use ▶ to start a service and 🔄 to restart it.\n"
        "Starting World will automatically ensure MySQL and Auth are running first."
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


def format_statuses(statuses: dict[str, object], database_online: bool) -> str:
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    running_count = sum(1 for status in statuses.values() if status.running)
    lines = [
        "🎮 Server Status",
        f"Updated: {updated_at}",
        f"Services online: {running_count}/3",
        f"Database login check: {'online' if database_online else 'offline'}",
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
    verb = "Start" if action == "start" else "Restart"
    service_name = {
        "mysql": "MySQL",
        "auth": "AuthServer",
        "world": "WorldServer",
    }.get(service_key, service_key)
    return f"⚡ {verb} {service_name}\n\n" + "\n".join(f"• {line}" for line in result_lines)


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

    application = ApplicationBuilder().token(config.bot_token).build()
    application.bot_data.update(
        {
            "config": config,
            "monitor": monitor,
            "controller": controller,
            "database": database,
        }
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", start_command))
    application.add_handler(CommandHandler("whoami", whoami_command))
    application.add_handler(CommandHandler("debugid", whoami_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("status", status_command))
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