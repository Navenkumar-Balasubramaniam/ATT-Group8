"""Data contract for the ATTPLANE dashboard pipeline.

This module is the single source of truth that "staples" inputs to outputs so the
prep script (``scripts/build_dashboard_data.py``), the notebooks, and ``app.py`` never
drift on file paths, file names, or expected columns.

Three tiers (see ``docs/data_contract.md`` for the human-readable version):

- inputs    -> ``data/raw/<table>.parquet``           (the 6 DB2 extracts)
- processed -> ``data/processed/<table>_clean.parquet`` + ``master_flight_dashboard.parquet``
- outputs   -> ``data/output/<name>.parquet``          (small dashboard-ready aggregates)

``app.py`` reads only the ``OUTPUT_FILES`` plus ``master_flight_dashboard.parquet``.
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping, Sequence

import polars as pl

from src import config

# --------------------------------------------------------------------------- #
# Directories (defined in src.config, re-exported here for the contract API)
# --------------------------------------------------------------------------- #
PROJECT_ROOT = config.PROJECT_ROOT
RAW_DIR = config.RAW_DIR
PROCESSED_DIR = config.PROCESSED_DIR
OUTPUT_DIR = config.OUTPUT_DIR

# --------------------------------------------------------------------------- #
# Tier 1: raw input tables
# --------------------------------------------------------------------------- #
RAW_TABLES: tuple[str, ...] = config.RAW_TABLES
RAW_FILES: dict[str, pathlib.Path] = {
    name: RAW_DIR / f"{name}.parquet" for name in RAW_TABLES
}

# ``tickets`` is huge (~248M rows / 3.4 GB). It is never read eagerly and is not
# materialised as a cleaned file: the prep script cleans it lazily and aggregates it
# with the streaming engine straight into the small revenue_* outputs. A global
# ``unique`` over it defeats streaming and exhausts memory, so it is intentionally
# excluded from the eager cleaning loop.
STREAMING_TABLES: tuple[str, ...] = config.STREAMING_TABLES

# Date / datetime columns to parse during cleaning (kept here so cleaning is
# consistent between the notebook and the prep script).
DATE_COLUMNS_BY_TABLE: dict[str, tuple[str, ...]] = config.DATE_COLUMNS_BY_TABLE
DATETIME_COLUMNS_BY_TABLE: dict[str, tuple[str, ...]] = config.DATETIME_COLUMNS_BY_TABLE

# --------------------------------------------------------------------------- #
# Tier 2: processed (cleaned + modelled) tables
# --------------------------------------------------------------------------- #
# Only the small tables get a materialised ``*_clean.parquet`` checkpoint. ``tickets``
# is not cleaned to disk (see STREAMING_TABLES); revenue is streamed straight to the outputs.
_CLEANED_TABLES = tuple(name for name in RAW_TABLES if name not in STREAMING_TABLES)
PROCESSED_FILES: dict[str, pathlib.Path] = {
    **{name: PROCESSED_DIR / f"{name}_clean.parquet" for name in _CLEANED_TABLES},
    "master": PROCESSED_DIR / "master_flight_dashboard.parquet",
}
MASTER_FILE: pathlib.Path = PROCESSED_FILES["master"]

# --------------------------------------------------------------------------- #
# Tier 3: dashboard-ready output aggregates (small; consumed by app.py)
# --------------------------------------------------------------------------- #
OUTPUT_FILES: dict[str, pathlib.Path] = {
    "flights_by_route": OUTPUT_DIR / "flights_by_route.parquet",
    "flights_by_continent": OUTPUT_DIR / "flights_by_continent.parquet",
    "fleet_usage": OUTPUT_DIR / "fleet_usage.parquet",
    "fleet_maintenance": OUTPUT_DIR / "fleet_maintenance.parquet",
    "revenue_by_route": OUTPUT_DIR / "revenue_by_route.parquet",
    "revenue_by_month": OUTPUT_DIR / "revenue_by_month.parquet",
    "revenue_by_class": OUTPUT_DIR / "revenue_by_class.parquet",
}

# Required columns per output: the contract app.py and the prep script agree on.
OUTPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "flights_by_route": (
        "route_code", "route_origin", "route_destination",
        "total_flights", "avg_distance_km", "avg_duration_min",
    ),
    "flights_by_continent": ("origin_continent", "total_flights", "total_distance_km"),
    "fleet_usage": ("airplane", "airplane_model", "total_flights", "total_distance_km"),
    "fleet_maintenance": (
        "airplane", "airplane_model", "airplane_build_date",
        "airplane_maintenance_flight_hours", "airplane_total_flight_distance",
        "aircraft_age_years",
    ),
    "revenue_by_route": (
        "route_code", "route_origin", "route_destination", "distance_band",
        "n_tickets", "total_revenue", "avg_ticket_price",
    ),
    "revenue_by_month": ("year", "month", "n_tickets", "total_revenue"),
    "revenue_by_class": ("class", "n_tickets", "total_revenue", "avg_ticket_price"),
}


def validate_output(df: pl.DataFrame, name: str) -> pl.DataFrame:
    """Assert a built output has the columns the contract promises.

    Returns the DataFrame unchanged so it can be used inline:
    ``validate_output(build_it(), "revenue_by_route").write_parquet(...)``.
    """
    expected = OUTPUT_COLUMNS.get(name)
    if expected is None:
        raise KeyError(f"Unknown output '{name}'. Known outputs: {sorted(OUTPUT_COLUMNS)}")

    missing = [column for column in expected if column not in df.columns]
    if missing:
        raise ValueError(
            f"Output '{name}' is missing required columns {missing}. "
            f"Got columns: {df.columns}"
        )
    return df


def ensure_dirs(directories: Sequence[pathlib.Path] = (RAW_DIR, PROCESSED_DIR, OUTPUT_DIR)) -> None:
    """Create the data directories if they do not exist yet."""
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def missing_files(files: Mapping[str, pathlib.Path]) -> list[str]:
    """Return the logical names of any files in ``files`` that do not exist."""
    return [name for name, path in files.items() if not path.exists()]
