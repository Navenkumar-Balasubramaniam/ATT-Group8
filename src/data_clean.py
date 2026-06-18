"""Very simple cleaning helpers for ATTPLANE parquet tables.

This module keeps cleaning beginner-friendly:

- keep the original column names
- trim text values
- turn common missing-value placeholders into nulls
- parse date columns only when you tell the function which columns are dates
- remove exact duplicate rows

There are no hardcoded ATTPLANE table names or column names in this module.

Large tables (for example ``tickets``, ~248M rows) cannot be read eagerly without
exhausting memory, so cleaning them eagerly crashes the kernel. For those, use the
streaming path (``clean_table_streaming``), which scans and sinks to disk through
Polars' out-of-core engine instead of materialising the whole frame. ``clean_raw_tables``
routes files above ``streaming_threshold_rows`` through that path automatically.
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping, Sequence

import polars as pl

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

MISSING_TEXT_VALUES = {"", "NA", "N/A", "NULL", "NONE", "NAN"}

# Files with more rows than this are cleaned with the streaming engine instead of
# being read eagerly into memory.
DEFAULT_STREAMING_THRESHOLD_ROWS = 5_000_000


# --------------------------------------------------------------------------- #
# Shared expression builders (work for both eager DataFrames and LazyFrames)
# --------------------------------------------------------------------------- #
def _missing_value_exprs(schema: Mapping[str, pl.DataType]) -> list[pl.Expr]:
    """Build trim + nullify-placeholder expressions for every text column."""
    expressions = []
    for column, dtype in schema.items():
        if dtype == pl.String:
            value = pl.col(column).str.strip_chars()
            is_missing = value.str.to_uppercase().is_in(MISSING_TEXT_VALUES)
            expressions.append(
                pl.when(is_missing).then(None).otherwise(value).alias(column)
            )
    return expressions


def _date_exprs(
    schema: Mapping[str, pl.DataType],
    date_columns: Sequence[str] = (),
    datetime_columns: Sequence[str] = (),
) -> list[pl.Expr]:
    """Build date/datetime parsing expressions for the requested columns.

    Columns already stored as the target type are skipped (no wasteful re-parse).
    """
    expressions = []

    for column in date_columns:
        if column in schema and schema[column] != pl.Date:
            expressions.append(
                pl.col(column)
                .cast(pl.String)
                .str.strptime(pl.Date, "%Y-%m-%d", strict=False)
                .alias(column)
            )

    for column in datetime_columns:
        if column in schema and schema[column].base_type() != pl.Datetime:
            value = pl.col(column).cast(pl.String)
            expressions.append(
                pl.coalesce(
                    value.str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S", strict=False),
                    value.str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S%.f", strict=False),
                ).alias(column)
            )

    return expressions


# --------------------------------------------------------------------------- #
# Eager cleaning (small/medium tables)
# --------------------------------------------------------------------------- #
def clean_missing_values(df: pl.DataFrame) -> pl.DataFrame:
    """Trim text columns and turn obvious missing values into nulls."""
    expressions = _missing_value_exprs(df.schema)
    if not expressions:
        return df
    return df.with_columns(expressions)


def parse_dates(
    df: pl.DataFrame,
    date_columns: Sequence[str] = (),
    datetime_columns: Sequence[str] = (),
) -> pl.DataFrame:
    """Parse selected date and datetime columns.

    Bad dates become null. Column names are passed in by the notebook or caller,
    not hardcoded in this module.
    """
    expressions = _date_exprs(df.schema, date_columns, datetime_columns)
    if not expressions:
        return df
    return df.with_columns(expressions)


def clean_dataframe(
    df: pl.DataFrame,
    *,
    date_columns: Sequence[str] = (),
    datetime_columns: Sequence[str] = (),
    drop_duplicates: bool = True,
) -> pl.DataFrame:
    """Clean one DataFrame."""
    df = clean_missing_values(df)
    df = parse_dates(
        df,
        date_columns=date_columns,
        datetime_columns=datetime_columns,
    )

    if drop_duplicates:
        df = df.unique(maintain_order=True)

    return df


# --------------------------------------------------------------------------- #
# Streaming cleaning (very large tables, e.g. tickets)
# --------------------------------------------------------------------------- #
def clean_table_streaming(
    raw_path: pathlib.Path,
    output_path: pathlib.Path,
    *,
    date_columns: Sequence[str] = (),
    datetime_columns: Sequence[str] = (),
    drop_duplicates: bool = True,
) -> pathlib.Path:
    """Clean one parquet file without loading it fully into memory.

    Applies the same cleaning rules as :func:`clean_dataframe` but builds a lazy
    plan and streams it straight to ``output_path`` via ``sink_parquet``. This is
    the path for files that are too large to read eagerly (e.g. ``tickets``).
    """
    raw_path = pathlib.Path(raw_path)
    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lf = pl.scan_parquet(raw_path)
    schema = lf.collect_schema()

    missing_exprs = _missing_value_exprs(schema)
    if missing_exprs:
        lf = lf.with_columns(missing_exprs)

    date_exprs = _date_exprs(schema, date_columns, datetime_columns)
    if date_exprs:
        lf = lf.with_columns(date_exprs)

    if drop_duplicates:
        # No maintain_order: ordering forces buffering and defeats streaming.
        lf = lf.unique()

    lf.sink_parquet(output_path)
    return output_path


def scan_clean_table(
    raw_path: pathlib.Path,
    *,
    date_columns: Sequence[str] = (),
    datetime_columns: Sequence[str] = (),
) -> pl.LazyFrame:
    """Return a *lazy* cleaned view of a parquet file (trim text + parse dates).

    No deduplication and nothing is materialised: the caller is expected to
    aggregate this with a streaming ``collect``. This is how very large tables
    (e.g. ``tickets``) are processed for analytics without writing a multi-GB
    intermediate file or running a memory-hostile global ``unique``.
    """
    lf = pl.scan_parquet(pathlib.Path(raw_path))
    schema = lf.collect_schema()

    missing_exprs = _missing_value_exprs(schema)
    if missing_exprs:
        lf = lf.with_columns(missing_exprs)

    date_exprs = _date_exprs(schema, date_columns, datetime_columns)
    if date_exprs:
        lf = lf.with_columns(date_exprs)

    return lf


# --------------------------------------------------------------------------- #
# Batch cleaning of a raw directory
# --------------------------------------------------------------------------- #
def _row_count(path: pathlib.Path) -> int:
    """Cheaply count rows in a parquet file without reading the data."""
    return pl.scan_parquet(path).select(pl.len()).collect().item()


def clean_raw_tables(
    raw_dir: pathlib.Path = RAW_DIR,
    output_dir: pathlib.Path | None = PROCESSED_DIR,
    *,
    date_columns_by_table: Mapping[str, Sequence[str]] | None = None,
    datetime_columns_by_table: Mapping[str, Sequence[str]] | None = None,
    drop_duplicates: bool = True,
    skip_errors: bool = True,
    streaming_tables: Sequence[str] = (),
    streaming_threshold_rows: int = DEFAULT_STREAMING_THRESHOLD_ROWS,
    exclude_tables: Sequence[str] = (),
) -> dict[str, pl.DataFrame]:
    """Clean each readable parquet file in ``raw_dir``.

    Files whose name is in ``streaming_tables`` or whose row count exceeds
    ``streaming_threshold_rows`` are cleaned with :func:`clean_table_streaming`
    and written to disk, but are **not** returned as eager frames (so the caller
    never holds a multi-hundred-million-row table in memory). Small tables are
    cleaned eagerly and returned in the result dict as before.
    """
    date_columns_by_table = date_columns_by_table or {}
    datetime_columns_by_table = datetime_columns_by_table or {}
    streaming_tables = set(streaming_tables)
    exclude_tables = set(exclude_tables)

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    cleaned_tables: dict[str, pl.DataFrame] = {}

    for path in sorted(raw_dir.glob("*.parquet")):
        table_name = path.stem

        if table_name in exclude_tables:
            continue

        try:
            use_streaming = table_name in streaming_tables
            if not use_streaming:
                use_streaming = _row_count(path) > streaming_threshold_rows

            if use_streaming:
                if output_dir is None:
                    print(f"Skipping {table_name}: streaming clean needs an output_dir")
                    continue
                clean_table_streaming(
                    path,
                    output_dir / f"{table_name}_clean.parquet",
                    date_columns=date_columns_by_table.get(table_name, ()),
                    datetime_columns=datetime_columns_by_table.get(table_name, ()),
                    drop_duplicates=drop_duplicates,
                )
                print(f"Streamed clean for large table '{table_name}' (not held in memory)")
                continue

            raw_df = pl.read_parquet(path)
            clean_df = clean_dataframe(
                raw_df,
                date_columns=date_columns_by_table.get(table_name, ()),
                datetime_columns=datetime_columns_by_table.get(table_name, ()),
                drop_duplicates=drop_duplicates,
            )
        except Exception as exc:
            if not skip_errors:
                raise
            print(f"Skipping {table_name}: {type(exc).__name__}: {exc}")
            continue

        cleaned_tables[table_name] = clean_df

        if output_dir is not None:
            clean_df.write_parquet(output_dir / f"{table_name}_clean.parquet")

    return cleaned_tables


if __name__ == "__main__":
    clean_raw_tables()
