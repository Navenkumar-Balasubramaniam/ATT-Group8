"""Very simple cleaning helpers for ATTPLANE parquet tables.

This module keeps cleaning beginner-friendly:

- keep the original column names
- trim text values
- turn common missing-value placeholders into nulls
- parse date columns only when you tell the function which columns are dates
- remove exact duplicate rows

There are no hardcoded ATTPLANE table names or column names in this module.
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping, Sequence

import polars as pl

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

MISSING_TEXT_VALUES = {"", "NA", "N/A", "NULL", "NONE", "NAN"}


def clean_missing_values(df: pl.DataFrame) -> pl.DataFrame:
    """Trim text columns and turn obvious missing values into nulls."""
    expressions = []

    for column, dtype in df.schema.items():
        if dtype == pl.String:
            value = pl.col(column).str.strip_chars()
            is_missing = value.str.to_uppercase().is_in(MISSING_TEXT_VALUES)

            expressions.append(
                pl.when(is_missing)
                .then(None)
                .otherwise(value)
                .alias(column)
            )

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
    expressions = []

    for column in date_columns:
        if column in df.columns:
            expressions.append(
                pl.col(column)
                .cast(pl.String)
                .str.strptime(pl.Date, "%Y-%m-%d", strict=False)
                .alias(column)
            )

    for column in datetime_columns:
        if column in df.columns:
            value = pl.col(column).cast(pl.String)
            expressions.append(
                pl.coalesce(
                    value.str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S", strict=False),
                    value.str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S%.f", strict=False),
                ).alias(column)
            )

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


def clean_raw_tables(
    raw_dir: pathlib.Path = RAW_DIR,
    output_dir: pathlib.Path | None = PROCESSED_DIR,
    *,
    date_columns_by_table: Mapping[str, Sequence[str]] | None = None,
    datetime_columns_by_table: Mapping[str, Sequence[str]] | None = None,
    drop_duplicates: bool = True,
    skip_errors: bool = True,
) -> dict[str, pl.DataFrame]:
    """Clean each readable parquet file in ``raw_dir``."""
    date_columns_by_table = date_columns_by_table or {}
    datetime_columns_by_table = datetime_columns_by_table or {}

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    cleaned_tables = {}

    for path in sorted(raw_dir.glob("*.parquet")):
        table_name = path.stem

        try:
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
