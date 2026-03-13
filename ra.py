from __future__ import annotations

from dataclasses import dataclass
import socket

from config import RemoteAccessConfig


PROMPT = "TC>"


class RemoteAccessError(RuntimeError):
    pass


@dataclass(frozen=True)
class RemoteAccessResult:
    command: str
    output: str


class RemoteAccessClient:
    def __init__(self, config: RemoteAccessConfig) -> None:
        self._config = config

    def run_command(self, command: str) -> RemoteAccessResult:
        clean_command = command.strip()
        if not clean_command:
            raise RemoteAccessError("RA command cannot be empty.")

        with socket.create_connection(
            (self._config.host, self._config.port),
            timeout=self._config.timeout_seconds,
        ) as connection:
            connection.settimeout(self._config.timeout_seconds)

            self._read_until(connection, "Username:")
            self._send_line(connection, self._config.username)

            self._read_until(connection, "Password:")
            self._send_line(connection, self._config.password)

            login_output = self._read_until(connection, PROMPT)
            if "Authentication failed" in login_output:
                raise RemoteAccessError("RA authentication failed.")

            self._send_line(connection, clean_command)
            command_output = self._read_until(connection, PROMPT)

        output = self._strip_prompt(command_output)
        return RemoteAccessResult(command=clean_command, output=output)

    def ping(self) -> bool:
        try:
            self.run_command("server info")
            return True
        except OSError:
            return False
        except RemoteAccessError:
            return False

    @staticmethod
    def _send_line(connection: socket.socket, value: str) -> None:
        connection.sendall(f"{value}\n".encode("utf-8"))

    @staticmethod
    def _read_until(connection: socket.socket, marker: str) -> str:
        chunks: list[bytes] = []
        marker_bytes = marker.encode("utf-8")

        while True:
            chunk = connection.recv(4096)
            if not chunk:
                raise RemoteAccessError(f"RA connection closed while waiting for {marker!r}.")
            chunks.append(chunk)
            combined = b"".join(chunks)
            if marker_bytes in combined:
                return combined.decode("utf-8", errors="replace")

    @staticmethod
    def _strip_prompt(output: str) -> str:
        normalized = output.replace("\r", "")
        if PROMPT in normalized:
            normalized = normalized.rsplit(PROMPT, 1)[0]
        return normalized.strip()