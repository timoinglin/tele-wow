from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import mysql.connector
from mysql.connector import MySQLConnection

from config import DatabaseConfig


class DatabaseClient:
    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config

    @contextmanager
    def connect(self) -> Iterator[MySQLConnection]:
        connection = mysql.connector.connect(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            database=self._config.database,
            autocommit=True,
        )
        try:
            yield connection
        finally:
            connection.close()

    def ping(self) -> bool:
        try:
            with self.connect() as connection:
                connection.ping(reconnect=False, attempts=1, delay=0)
            return True
        except mysql.connector.Error:
            return False

    def create_account(self, username: str, password: str) -> None:
        raise NotImplementedError(
            "Account creation is reserved for phase 2, when the exact MoP SRP6 schema is confirmed."
        )