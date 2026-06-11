"""Database connection and table-loading helpers.

This module should own the DB2 connection code and any reusable SQL read helpers.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    name: str
    username: str
    password: str


def build_connection_string(config: DatabaseConfig) -> str:
    """Return a DB2 connection string for the group account."""
    return (
        f"HOSTNAME={config.host};PORT={config.port};DATABASE={config.name};"
        f"PROTOCOL=TCPIP;UID={config.username};PWD={config.password};"
        f"AUTHENTICATION=SERVER;CURRENTSCHEMA={config.username.upper()};"
    )


def read_table_placeholder(*_: object, **__: object) -> pl.DataFrame:
    """Placeholder for a reusable DB read helper."""
    raise NotImplementedError("Implement DB2 table loading here.")
