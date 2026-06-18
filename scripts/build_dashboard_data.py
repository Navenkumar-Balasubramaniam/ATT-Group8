"""Build every dashboard-ready dataset from ``data/raw`` -- no database needed.

This is the one-time prep step. It produces the files described in the data
contract (``docs/data_contract.md`` / ``src/contracts.py``) so the Streamlit app
can read small, pre-aggregated parquet files instead of touching the 248M-row
tickets table at runtime.

Run from the repo root:

    uv run python scripts/build_dashboard_data.py

It is idempotent and safe to re-run. The tickets step uses the streaming engine
(``scan_parquet`` -> ``sink_parquet``) so the big file is never read into memory.
"""

from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path

import polars as pl

# Make ``import src...`` work whether run as a script or a module.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import analysis, contracts  # noqa: E402
from src.data_clean import clean_raw_tables, scan_clean_table  # noqa: E402
from src.data_enrich import enrich_tables  # noqa: E402
from src.data_model import (  # noqa: E402
    check_flight_dashboard_joins,
    make_flight_dashboard_table,
)


def _log(message: str) -> None:
    print(f"[build] {message}", flush=True)


def step_clean_tables() -> dict[str, pl.DataFrame]:
    """Clean the small raw tables eagerly.

    ``tickets`` is excluded here: it is far too large to clean eagerly, and a
    global ``unique`` over ~248M rows defeats streaming and exhausts memory.
    Instead it is cleaned lazily and aggregated directly in ``step_revenue_aggregates``.
    """
    _log("Cleaning small raw tables (tickets is handled separately, streamed)...")
    start = time.perf_counter()
    cleaned = clean_raw_tables(
        raw_dir=contracts.RAW_DIR,
        output_dir=contracts.PROCESSED_DIR,
        date_columns_by_table=contracts.DATE_COLUMNS_BY_TABLE,
        datetime_columns_by_table=contracts.DATETIME_COLUMNS_BY_TABLE,
        exclude_tables=contracts.STREAMING_TABLES,
        skip_errors=False,
    )
    _log(f"Cleaned small tables {sorted(cleaned)} in {time.perf_counter() - start:.1f}s")
    return cleaned


def step_build_master(cleaned: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]:
    """Enrich the small tables and build the master flight dashboard table."""
    _log("Enriching tables and building master_flight_dashboard...")
    enriched = enrich_tables(cleaned, reference_date=date.today())

    required = {"flights", "routes", "airplanes", "airports"}
    missing = required - set(enriched)
    if missing:
        raise RuntimeError(f"Cannot build master table; missing cleaned tables: {sorted(missing)}")

    master = make_flight_dashboard_table(
        enriched["flights"],
        enriched["routes"],
        enriched["airplanes"],
        enriched["airports"],
    )

    checks = check_flight_dashboard_joins(
        enriched["flights"],
        enriched["routes"],
        enriched["airplanes"],
        enriched["airports"],
        master,
    )
    if not bool(checks.get_column("row_count_ok").all()):
        _log("WARNING: join row-count check failed:")
        print(checks)

    master.write_parquet(contracts.MASTER_FILE)
    _log(f"Wrote {contracts.MASTER_FILE.name}: {master.height:,} rows x {master.width} cols")
    return enriched


def step_flight_aggregates(master: pl.DataFrame) -> None:
    """Build the route/fleet aggregates from the master table."""
    _log("Building flight & fleet aggregates...")
    builders = {
        "flights_by_route": analysis.flights_by_route,
        "flights_by_continent": analysis.flights_by_continent,
        "fleet_usage": analysis.fleet_usage,
        "fleet_maintenance": analysis.fleet_maintenance,
    }
    for name, build in builders.items():
        result = contracts.validate_output(build(master), name)
        result.write_parquet(contracts.OUTPUT_FILES[name])
        _log(f"  {name}: {result.shape}")


def step_revenue_aggregates(enriched: dict[str, pl.DataFrame]) -> None:
    """Build revenue aggregates by streaming over raw tickets (never fully loaded)."""
    _log("Building revenue aggregates (streaming scan of raw tickets)...")
    start = time.perf_counter()
    tickets = scan_clean_table(
        contracts.RAW_FILES["tickets"],
        datetime_columns=contracts.DATETIME_COLUMNS_BY_TABLE.get("tickets", ()),
    )

    by_route = contracts.validate_output(
        analysis.revenue_by_route(tickets, enriched["routes"]), "revenue_by_route"
    )
    by_route.write_parquet(contracts.OUTPUT_FILES["revenue_by_route"])
    _log(f"  revenue_by_route: {by_route.shape}")

    by_month = contracts.validate_output(analysis.revenue_by_month(tickets), "revenue_by_month")
    by_month.write_parquet(contracts.OUTPUT_FILES["revenue_by_month"])
    _log(f"  revenue_by_month: {by_month.shape}")

    by_class = contracts.validate_output(analysis.revenue_by_class(tickets), "revenue_by_class")
    by_class.write_parquet(contracts.OUTPUT_FILES["revenue_by_class"])
    _log(f"  revenue_by_class: {by_class.shape}")

    _log(f"Revenue aggregates done in {time.perf_counter() - start:.1f}s")


def main() -> None:
    overall = time.perf_counter()
    contracts.ensure_dirs()

    cleaned = step_clean_tables()
    enriched = step_build_master(cleaned)
    master = pl.read_parquet(contracts.MASTER_FILE)
    step_flight_aggregates(master)
    step_revenue_aggregates(enriched)

    still_missing = contracts.missing_files(contracts.OUTPUT_FILES)
    if still_missing:
        _log(f"WARNING: these outputs were not produced: {still_missing}")
    else:
        _log("All contract outputs present in data/output/.")
    _log(f"Done in {time.perf_counter() - overall:.1f}s. Run: uv run streamlit run app.py")


if __name__ == "__main__":
    main()
