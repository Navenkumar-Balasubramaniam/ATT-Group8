"""Simple helpers for inspecting ATTPLANE parquet tables.

This module only looks at the data. It does not clean or change anything.

Suggested notebook order:
1. check which tables are available
2. load and display the tables
3. show simple summary statistics
4. count missing/null values
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping

import polars as pl

from src import config

PROJECT_ROOT = config.PROJECT_ROOT
RAW_DIR = config.RAW_DIR
PROCESSED_DIR = config.PROCESSED_DIR

RAW_TABLES = config.RAW_TABLES


def check_raw_files(
    raw_dir: pathlib.Path = RAW_DIR,
    table_names: tuple[str, ...] = RAW_TABLES,
) -> pl.DataFrame:
    """Return one row per expected raw parquet file."""
    rows = []

    for table_name in table_names:
        path = raw_dir / f"{table_name}.parquet"

        if not path.exists():
            rows.append(
                {
                    "table": table_name,
                    "status": "missing",
                    "rows": None,
                    "columns": None,
                    "issue": "file does not exist",
                }
            )
            continue

        try:
            rows.append(
                {
                    "table": table_name,
                    "status": "ok",
                    "rows": pl.scan_parquet(path).select(pl.len()).collect().item(),
                    "columns": len(pl.read_parquet(path, n_rows=1).columns),
                    "issue": None,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "table": table_name,
                    "status": "needs_repull",
                    "rows": None,
                    "columns": None,
                    "issue": f"{type(exc).__name__}: {exc}",
                }
            )

    return pl.DataFrame(rows)


def load_tables(
    data_dir: pathlib.Path = RAW_DIR,
    table_names: tuple[str, ...] = RAW_TABLES,
    sample_rows: int | None = None,
    *,
    skip_errors: bool = True,
) -> dict[str, pl.DataFrame]:
    """Load parquet tables into a dictionary.

    Use ``sample_rows`` in the notebook when you only need a quick preview.
    """
    tables = {}

    for table_name in table_names:
        path = data_dir / f"{table_name}.parquet"

        try:
            tables[table_name] = pl.read_parquet(path, n_rows=sample_rows)
        except Exception as exc:
            if not skip_errors:
                raise
            print(f"Skipping {table_name}: {type(exc).__name__}: {exc}")

    return tables


def summary_statistics(tables: Mapping[str, pl.DataFrame]) -> pl.DataFrame:
    """Return simple min/mean/median/max statistics for numeric columns."""
    schema = {
        "table": pl.String,
        "column": pl.String,
        "min": pl.Float64,
        "mean": pl.Float64,
        "median": pl.Float64,
        "max": pl.Float64,
    }
    rows = []

    for table_name, df in tables.items():
        for column, dtype in df.schema.items():
            if not dtype.is_numeric():
                continue

            value = pl.col(column).cast(pl.Float64)
            stats = df.select(
                value.min().alias("min"),
                value.mean().alias("mean"),
                value.median().alias("median"),
                value.max().alias("max"),
            ).to_dicts()[0]

            rows.append({"table": table_name, "column": column, **stats})

    return pl.DataFrame(rows, schema=schema).sort(["table", "column"])


def missing_value_counts(tables: Mapping[str, pl.DataFrame]) -> pl.DataFrame:
    """Count null values and blank strings for each column."""
    schema = {
        "table": pl.String,
        "column": pl.String,
        "dtype": pl.String,
        "rows": pl.Int64,
        "null_count": pl.Int64,
        "blank_string_count": pl.Int64,
        "missing_count": pl.Int64,
        "missing_pct": pl.Float64,
    }
    rows = []

    for table_name, df in tables.items():
        for column, dtype in df.schema.items():
            null_count = df[column].null_count()

            if dtype == pl.String:
                blank_count = df.select(
                    (pl.col(column).str.strip_chars() == "").sum()
                ).item()
            else:
                blank_count = 0

            missing_count = null_count + blank_count
            rows.append(
                {
                    "table": table_name,
                    "column": column,
                    "dtype": str(dtype),
                    "rows": df.height,
                    "null_count": null_count,
                    "blank_string_count": blank_count,
                    "missing_count": missing_count,
                    "missing_pct": missing_count / df.height if df.height else None,
                }
            )

    return pl.DataFrame(rows, schema=schema).sort(
        ["table", "missing_count", "column"],
        descending=[False, True, False],
    )
