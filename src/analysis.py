"""Analytical aggregations and business metric helpers.

Cleaning belongs in ``src.data_clean``. Feature engineering and joined modeling
tables belong in ``src.data_enrich``. This module holds the actual analysis used by
the dashboard: route traffic, fleet utilization, and ticket revenue summaries.

Two families of functions:

- ``flights_*`` / ``fleet_*`` operate on the in-memory master flight table
  (``master_flight_dashboard.parquet``, ~1.76M rows -- fine eagerly).
- ``revenue_*`` operate on a *lazy* scan of the cleaned tickets table
  (~248M rows) so they never load all of it into memory.

All return small DataFrames ready to write to ``data/output/``.
"""

from __future__ import annotations

import polars as pl

from src import config

# Reference year for aircraft age, matching the project's existing convention.
AGE_REFERENCE_YEAR = config.AGE_REFERENCE_YEAR


def _collect_streaming(lf: pl.LazyFrame) -> pl.DataFrame:
    """Collect a lazy plan with the out-of-core streaming engine.

    Used for aggregations over the ~248M-row tickets scan so the data is never
    held in memory all at once. Falls back across Polars API versions.
    """
    try:
        return lf.collect(engine="streaming")
    except TypeError:
        return lf.collect(streaming=True)


# --------------------------------------------------------------------------- #
# Flight traffic and fleet utilization (from the master table)
# --------------------------------------------------------------------------- #
def flights_by_route(master: pl.DataFrame) -> pl.DataFrame:
    """Top routes by number of flights."""
    return (
        master.lazy()
        .group_by("route_code", "route_origin", "route_destination")
        .agg(
            pl.len().alias("total_flights"),
            pl.col("route_distance").mean().alias("avg_distance_km"),
            pl.col("route_flight_minutes").mean().alias("avg_duration_min"),
        )
        .sort("total_flights", descending=True)
        .collect()
    )


def flights_by_continent(master: pl.DataFrame) -> pl.DataFrame:
    """Flight volume by origin continent."""
    return (
        master.lazy()
        .group_by("origin_continent")
        .agg(
            pl.len().alias("total_flights"),
            pl.col("route_distance").sum().alias("total_distance_km"),
        )
        .sort("total_flights", descending=True)
        .collect()
    )


def fleet_usage(master: pl.DataFrame) -> pl.DataFrame:
    """Flights and distance per aircraft."""
    return (
        master.lazy()
        .group_by("airplane", "airplane_model")
        .agg(
            pl.len().alias("total_flights"),
            pl.col("route_distance").sum().alias("total_distance_km"),
        )
        .sort("total_flights", descending=True)
        .collect()
    )


def fleet_maintenance(master: pl.DataFrame) -> pl.DataFrame:
    """Aircraft age vs maintenance hours for a scatter plot."""
    return (
        master.lazy()
        .select(
            "airplane",
            "airplane_model",
            "airplane_build_date",
            "airplane_maintenance_flight_hours",
            "airplane_total_flight_distance",
        )
        .unique()
        .with_columns(
            (AGE_REFERENCE_YEAR - pl.col("airplane_build_date").cast(pl.Date).dt.year())
            .alias("aircraft_age_years")
        )
        .collect()
    )


# --------------------------------------------------------------------------- #
# Ticket revenue (lazy scan of cleaned tickets -- never fully materialised)
# --------------------------------------------------------------------------- #
def revenue_by_route(tickets: pl.LazyFrame, routes: pl.DataFrame) -> pl.DataFrame:
    """Revenue, ticket volume, and average price per route.

    ``tickets`` is a LazyFrame (``pl.scan_parquet(tickets_clean.parquet)``); the
    group_by streams over the file. The small per-route result is then joined to
    ``routes`` for origin/destination/distance_band labels.
    """
    per_route = _collect_streaming(
        tickets.group_by("route_code").agg(
            pl.len().alias("n_tickets"),
            pl.col("total_amount").sum().alias("total_revenue"),
            pl.col("price").mean().alias("avg_ticket_price"),
        )
    )

    route_labels = routes.select(
        "route_code",
        pl.col("origin").alias("route_origin"),
        pl.col("destination").alias("route_destination"),
        "distance_band",
    )

    return (
        per_route.join(route_labels, on="route_code", how="left")
        .select(
            "route_code",
            "route_origin",
            "route_destination",
            "distance_band",
            "n_tickets",
            "total_revenue",
            "avg_ticket_price",
        )
        .sort("total_revenue", descending=True)
    )


def revenue_by_month(tickets: pl.LazyFrame) -> pl.DataFrame:
    """Total revenue and ticket volume per departure month."""
    result = _collect_streaming(
        tickets.select(
            pl.col("departure").dt.year().alias("year"),
            pl.col("departure").dt.month().alias("month"),
            pl.col("total_amount"),
        )
        .group_by("year", "month")
        .agg(
            pl.len().alias("n_tickets"),
            pl.col("total_amount").sum().alias("total_revenue"),
        )
    )
    return result.sort("year", "month")


def revenue_by_class(tickets: pl.LazyFrame) -> pl.DataFrame:
    """Revenue, ticket volume, and average price per cabin class."""
    result = _collect_streaming(
        tickets.group_by("class").agg(
            pl.len().alias("n_tickets"),
            pl.col("total_amount").sum().alias("total_revenue"),
            pl.col("price").mean().alias("avg_ticket_price"),
        )
    )
    return result.sort("total_revenue", descending=True)
