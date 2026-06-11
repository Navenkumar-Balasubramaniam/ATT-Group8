"""Extract all 6 database tables and save them as Parquet files to data/raw/.

Usage (from repo root):
    python -m src.pull_data

Already-downloaded tables are skipped automatically on re-run.
Large tables are fetched in chunks to stay within memory limits.
"""

from __future__ import annotations

import pathlib
import time

import polars as pl

from src.db import (
    DatabaseConfig,
    get_engine,
    read_table,
    stream_table_to_parquet,
)

SCHEMA = "ATTGRP8"
TABLES = [
    "AIRPLANES", "AIRPORTS", "FLIGHTS",
    "PASSENGERS", "ROUTES", "TICKETS",
]
RAW_DIR = pathlib.Path(__file__).parent.parent / "data" / "raw"
CHUNK_SIZE = 50_000

DEFAULT_CONFIG = DatabaseConfig(
    host="52.211.123.34",
    port=25010,
    name="ATTPLANE",
    username="attgrp8",
    password="bigdata",
)


def pull_all_tables(
    config: DatabaseConfig = DEFAULT_CONFIG,
) -> dict[str, pl.DataFrame]:
    """Connect to DB2 and pull all 6 tables as Polars DataFrames.

    Returns a dict mapping uppercase table name -> DataFrame.
    Only suitable for tables that fit in memory (use pull_and_save for ETL).
    """
    engine = get_engine(config)
    tables: dict[str, pl.DataFrame] = {}
    total = len(TABLES)
    for i, table in enumerate(TABLES, 1):
        print(f"  [{i}/{total}] {table} ... ", end="", flush=True)
        t0 = time.monotonic()
        tables[table] = read_table(engine, table, SCHEMA)
        elapsed = time.monotonic() - t0
        rows = len(tables[table])
        cols = len(tables[table].columns)
        print(f"{rows:,} rows  {cols} cols  ({elapsed:.1f}s)")
    return tables


def save_tables(
    tables: dict[str, pl.DataFrame],
    output_dir: pathlib.Path = RAW_DIR,
) -> None:
    """Write each DataFrame to a Parquet file in output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        path = output_dir / f"{name.lower()}.parquet"
        df.write_parquet(path)
        print(f"  Saved {path}  ({len(df):,} rows)")


def pull_and_save(
    config: DatabaseConfig = DEFAULT_CONFIG,
    output_dir: pathlib.Path = RAW_DIR,
) -> dict[str, pathlib.Path]:
    """Pull missing tables from DB2 and save each as Parquet immediately.

    - Skips any table whose .parquet file already exists in output_dir.
    - Fetches in CHUNK_SIZE-row batches to avoid MemoryError on large tables.
    - Returns a dict mapping table name -> parquet path for every table.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    missing = [
        t for t in TABLES
        if not (output_dir / f"{t.lower()}.parquet").exists()
    ]

    if not missing:
        print("All 6 tables already present in", output_dir)
        return {t: output_dir / f"{t.lower()}.parquet" for t in TABLES}

    print(
        f"Connecting to {config.host}:{config.port}/{config.name}"
        f" as {config.username} ...",
        flush=True,
    )
    engine = get_engine(config)
    total = len(TABLES)
    t_start = time.monotonic()
    paths: dict[str, pathlib.Path] = {}

    for i, table in enumerate(TABLES, 1):
        path = output_dir / f"{table.lower()}.parquet"
        prefix = f"  [{i}/{total}] {table}"

        if path.exists():
            print(f"{prefix} ... already exists, skipping", flush=True)
            paths[table] = path
            continue

        print(f"{prefix} ...", flush=True)
        t0 = time.monotonic()

        def _on_chunk(n: int, _p: str = prefix) -> None:
            print(f"    {n:>10,} rows fetched ...", flush=True)

        rows = stream_table_to_parquet(
            engine, table, SCHEMA, path, CHUNK_SIZE, _on_chunk
        )
        elapsed = time.monotonic() - t0
        print(
            f"  -> {path.name}: {rows:,} rows  ({elapsed:.1f}s)",
            flush=True,
        )
        paths[table] = path

    total_s = time.monotonic() - t_start
    print(f"\nDone.  Total time: {total_s:.1f}s")
    return paths


if __name__ == "__main__":
    pull_and_save()
