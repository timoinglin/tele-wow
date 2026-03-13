from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass(frozen=True)
class ServiceConfig:
    key: str
    display_name: str
    process_name: str
    command: tuple[str, ...]
    working_directory: Path


@dataclass(frozen=True)
class AppConfig:
    repo_root: Path
    app_root: Path
    bot_token: str
    allowed_user_ids: tuple[int, ...]
    alert_chat_id: int
    poll_interval_seconds: int
    monitor_disk_path: Path
    database: DatabaseConfig
    mysql: ServiceConfig
    auth: ServiceConfig
    world: ServiceConfig

    @property
    def services(self) -> dict[str, ServiceConfig]:
        return {
            self.mysql.key: self.mysql,
            self.auth.key: self.auth,
            self.world.key: self.world,
        }


def _require_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")
    return value.strip()


def _load_int(name: str, default: int | None = None) -> int:
    raw_default = None if default is None else str(default)
    value = _require_env(name, raw_default)
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer") from exc


def _load_allowed_user_ids() -> tuple[int, ...]:
    raw_value = os.getenv("TELEGRAM_ALLOWED_USER_IDS")
    if raw_value and raw_value.strip():
        user_ids: list[int] = []
        for item in raw_value.split(","):
            candidate = item.strip()
            if not candidate:
                continue
            try:
                user_ids.append(int(candidate))
            except ValueError as exc:
                raise ValueError("Environment variable TELEGRAM_ALLOWED_USER_IDS must contain integers") from exc

        if not user_ids:
            raise ValueError("Environment variable TELEGRAM_ALLOWED_USER_IDS must contain at least one user ID")
        return tuple(dict.fromkeys(user_ids))

    return (_load_int("TELEGRAM_ALLOWED_USER_ID"),)


def _resolve_path(raw_value: str, *, base_path: Path) -> Path:
    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        candidate = (base_path / candidate).resolve()
    return candidate


def load_config(env_path: str | Path | None = None) -> AppConfig:
    app_root = Path(__file__).resolve().parent
    repo_root = app_root
    env_file = Path(env_path) if env_path else app_root / ".env"
    load_dotenv(env_file)

    bot_token = _require_env("TELEGRAM_BOT_TOKEN")
    allowed_user_ids = _load_allowed_user_ids()
    alert_chat_id = _load_int("TELEGRAM_ALERT_CHAT_ID", allowed_user_ids[0])
    poll_interval_seconds = _load_int("POLL_INTERVAL_SECONDS", 15)
    monitor_disk_path = _resolve_path(
        _require_env("MONITOR_DISK_PATH", ".."),
        base_path=repo_root,
    )

    database = DatabaseConfig(
        host=_require_env("DB_HOST", "127.0.0.1"),
        port=_load_int("DB_PORT", 3306),
        user=_require_env("DB_USER", "root"),
        password=_require_env("DB_PASSWORD", "ascent"),
        database=_require_env("DB_NAME", "mop_auth"),
    )

    mysql_working_dir = _resolve_path(
        _require_env("MYSQL_WORKING_DIR", "../Database/_Server"),
        base_path=repo_root,
    )
    auth_working_dir = _resolve_path(
        _require_env("AUTHSERVER_WORKING_DIR", "../Repack"),
        base_path=repo_root,
    )
    world_working_dir = _resolve_path(
        _require_env("WORLDSERVER_WORKING_DIR", "../Repack"),
        base_path=repo_root,
    )

    mysql_start_script = _resolve_path(
        _require_env("MYSQL_START_SCRIPT", "../Database/_Server/MySQL.bat"),
        base_path=repo_root,
    )
    auth_executable = _resolve_path(
        _require_env("AUTHSERVER_PATH", "../Repack/authserver.exe"),
        base_path=repo_root,
    )
    world_executable = _resolve_path(
        _require_env("WORLDSERVER_PATH", "../Repack/worldserver.exe"),
        base_path=repo_root,
    )

    return AppConfig(
        repo_root=repo_root,
        app_root=app_root,
        bot_token=bot_token,
        allowed_user_ids=allowed_user_ids,
        alert_chat_id=alert_chat_id,
        poll_interval_seconds=poll_interval_seconds,
        monitor_disk_path=monitor_disk_path,
        database=database,
        mysql=ServiceConfig(
            key="mysql",
            display_name="MySQL",
            process_name=_require_env("MYSQL_PROCESS_NAME", "mysqld.exe"),
            command=("cmd.exe", "/c", str(mysql_start_script)),
            working_directory=mysql_working_dir,
        ),
        auth=ServiceConfig(
            key="auth",
            display_name="AuthServer",
            process_name=_require_env("AUTHSERVER_PROCESS_NAME", "authserver.exe"),
            command=(str(auth_executable),),
            working_directory=auth_working_dir,
        ),
        world=ServiceConfig(
            key="world",
            display_name="WorldServer",
            process_name=_require_env("WORLDSERVER_PROCESS_NAME", "worldserver.exe"),
            command=(str(world_executable),),
            working_directory=world_working_dir,
        ),
    )