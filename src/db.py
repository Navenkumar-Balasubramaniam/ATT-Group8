"""Database connection and table-loading helpers."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Callable

import pandas as pd
import polars as pl
from sqlalchemy import create_engine


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


def get_engine(config: DatabaseConfig):
    """Return a SQLAlchemy engine for a DB2 connection using ibm_db."""
    import ibm_db
    import ibm_db_dbi as _dbi

    conn_str = build_connection_string(config)

    def _make_conn():
        return _dbi.Connection(ibm_db.connect(conn_str, "", ""))

    return create_engine("ibm_db_sa://", creator=_make_conn)


def read_table(engine, table_name: str, schema: str) -> pl.DataFrame:
    """Read a full table from DB2 and return it as a Polars DataFrame.

    Column names are lowercased for Python-friendly access.
    Only suitable for small/medium tables that fit in memory.
    """
    query = f'SELECT * FROM "{schema}"."{table_name}"'
    with engine.connect() as conn:
        df_pd = pd.read_sql_query(query, conn)
    df_pd.columns = [c.lower() for c in df_pd.columns]
    return pl.from_pandas(df_pd)


def stream_table_to_parquet(
    engine,
    table_name: str,
    schema: str,
    path: pathlib.Path,
    chunk_size: int = 50_000,
    on_chunk: Callable[[int], None] | None = None,
) -> int:
    """Fetch a table in chunks and write directly to a Parquet file.

    Keeps only chunk_size rows in memory at a time — safe for large tables.
    Calls on_chunk(total_rows_so_far) after each chunk if provided.
    Returns the total row count.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    query = f'SELECT * FROM "{schema}"."{table_name}"'
    writer: pq.ParquetWriter | None = None
    total_rows = 0

    try:
        with engine.connect() as conn:
            for chunk in pd.read_sql_query(
                query, conn, chunksize=chunk_size
            ):
                chunk.columns = [c.lower() for c in chunk.columns]
                arrow_tbl = pa.Table.from_pandas(
                    chunk, preserve_index=False
                )
                if writer is None:
                    writer = pq.ParquetWriter(path, arrow_tbl.schema)
                writer.write_table(arrow_tbl)
                total_rows += len(chunk)
                if on_chunk is not None:
                    on_chunk(total_rows)
    finally:
        if writer is not None:
            writer.close()

    return total_rows
