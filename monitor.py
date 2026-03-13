from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import time
from typing import Iterable

import psutil

from config import AppConfig, ServiceConfig


CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    started_at: float | None


@dataclass(frozen=True)
class ServiceStatus:
    key: str
    display_name: str
    running: bool
    pid: int | None
    started_at: float | None
    memory_mb: float | None


class ProcessMonitor:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._last_state: dict[str, bool] = {}
        self._suppressed_until: dict[str, float] = {}

    def seed_state(self) -> None:
        for service in self._config.services.values():
            self._last_state[service.key] = is_process_running(service.process_name)

    def suppress(self, service_key: str, seconds: int = 45) -> None:
        self._suppressed_until[service_key] = time.time() + seconds

    def detect_crashes(self) -> list[ServiceStatus]:
        crashed_services: list[ServiceStatus] = []
        now = time.time()

        for service in self._config.services.values():
            running_process = find_process(service.process_name)
            is_running = running_process is not None
            previous_state = self._last_state.get(service.key, is_running)
            suppressed_until = self._suppressed_until.get(service.key, 0.0)

            if is_running:
                self._last_state[service.key] = True
                continue

            if suppressed_until > now:
                continue

            if previous_state:
                crashed_services.append(
                    ServiceStatus(
                        key=service.key,
                        display_name=service.display_name,
                        running=False,
                        pid=None,
                    )
                )

            self._last_state[service.key] = False

        return crashed_services


class ServerController:
    def __init__(self, config: AppConfig, monitor: ProcessMonitor | None = None) -> None:
        self._config = config
        self._monitor = monitor

    def get_service_statuses(self) -> dict[str, ServiceStatus]:
        statuses: dict[str, ServiceStatus] = {}
        for service in self._config.services.values():
            process = find_process(service.process_name)
            started_at = None
            memory_mb = None
            if process is not None:
                try:
                    with process.oneshot():
                        started_at = process.create_time()
                        memory_mb = round(process.memory_info().rss / (1024 ** 2), 1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    process = None
            statuses[service.key] = ServiceStatus(
                key=service.key,
                display_name=service.display_name,
                running=process is not None,
                pid=None if process is None else process.pid,
                started_at=started_at,
                memory_mb=memory_mb,
            )
        return statuses

    def get_system_stats(self) -> dict[str, float | str]:
        disk_usage = psutil.disk_usage(str(self._config.monitor_disk_path))
        virtual_memory = psutil.virtual_memory()
        boot_time = psutil.boot_time()
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "cpu_count_logical": psutil.cpu_count(logical=True) or 0,
            "cpu_count_physical": psutil.cpu_count(logical=False) or 0,
            "memory_percent": virtual_memory.percent,
            "memory_used_gb": round(virtual_memory.used / (1024 ** 3), 2),
            "memory_total_gb": round(virtual_memory.total / (1024 ** 3), 2),
            "memory_available_gb": round(virtual_memory.available / (1024 ** 3), 2),
            "disk_percent": disk_usage.percent,
            "disk_used_gb": round(disk_usage.used / (1024 ** 3), 2),
            "disk_total_gb": round(disk_usage.total / (1024 ** 3), 2),
            "disk_free_gb": round(disk_usage.free / (1024 ** 3), 2),
            "disk_path": str(self._config.monitor_disk_path),
            "boot_time": boot_time,
        }

    def start_service(self, service_key: str) -> list[str]:
        messages: list[str] = []
        for dependency_key in self._dependency_order_for_start(service_key):
            messages.extend(self._start_single_service(self._config.services[dependency_key]))
        return messages

    def restart_service(self, service_key: str) -> list[str]:
        if service_key == "mysql":
            return self._restart_mysql_stack()
        if service_key == "auth":
            return self._restart_auth_stack()

        service = self._config.services[service_key]
        return self._restart_single_service(service)

    def _restart_mysql_stack(self) -> list[str]:
        messages: list[str] = []
        statuses = self.get_service_statuses()

        if statuses["world"].running:
            messages.extend(self._stop_single_service(self._config.world))
        if statuses["auth"].running:
            messages.extend(self._stop_single_service(self._config.auth))
        messages.extend(self._stop_single_service(self._config.mysql))
        time.sleep(2)

        messages.extend(self._start_single_service(self._config.mysql))
        if statuses["auth"].running or statuses["world"].running:
            messages.extend(self._start_single_service(self._config.auth))
        if statuses["world"].running:
            messages.extend(self._start_single_service(self._config.world))
        return messages

    def _restart_auth_stack(self) -> list[str]:
        messages: list[str] = []
        statuses = self.get_service_statuses()

        if statuses["world"].running:
            messages.extend(self._stop_single_service(self._config.world))
        messages.extend(self._stop_single_service(self._config.auth))
        time.sleep(2)

        messages.extend(self._start_single_service(self._config.auth))
        if statuses["world"].running:
            messages.extend(self._start_single_service(self._config.world))
        return messages

    def _restart_single_service(self, service: ServiceConfig) -> list[str]:
        messages = self._stop_single_service(service)
        time.sleep(2)
        messages.extend(self._start_single_service(service))
        return messages

    def _start_single_service(self, service: ServiceConfig) -> list[str]:
        if is_process_running(service.process_name):
            return [f"{service.display_name} is already running."]

        self._validate_service_target(service)
        subprocess.Popen(
            service.command,
            cwd=service.working_directory,
            creationflags=CREATE_NEW_CONSOLE,
        )
        time.sleep(2)

        if is_process_running(service.process_name):
            return [f"Started {service.display_name}."]
        return [f"Tried to start {service.display_name}, but the process is not visible yet."]

    def _stop_single_service(self, service: ServiceConfig) -> list[str]:
        process = find_process(service.process_name)
        if process is None:
            return [f"{service.display_name} is not running."]

        if self._monitor is not None:
            self._monitor.suppress(service.key)

        process.terminate()
        try:
            process.wait(timeout=15)
            return [f"Stopped {service.display_name}."]
        except psutil.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
            return [f"Force-stopped {service.display_name}."]

    def _dependency_order_for_start(self, service_key: str) -> list[str]:
        if service_key == "mysql":
            return ["mysql"]
        if service_key == "auth":
            return ["mysql", "auth"]
        if service_key == "world":
            return ["mysql", "auth", "world"]
        raise KeyError(f"Unknown service key: {service_key}")

    @staticmethod
    def _validate_service_target(service: ServiceConfig) -> None:
        command_target = Path(service.command[-1])
        if not command_target.exists():
            raise FileNotFoundError(f"Launch target not found for {service.display_name}: {command_target}")
        if not service.working_directory.exists():
            raise FileNotFoundError(
                f"Working directory not found for {service.display_name}: {service.working_directory}"
            )


def find_process(process_name: str) -> psutil.Process | None:
    expected_name = process_name.lower()
    for process in _iter_processes():
        name = (process.info.get("name") or "").lower()
        if name == expected_name:
            return process
    return None


def is_process_running(process_name: str) -> bool:
    return find_process(process_name) is not None


def _iter_processes() -> Iterable[psutil.Process]:
    for process in psutil.process_iter(["name"]):
        try:
            yield process
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue