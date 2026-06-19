"""Join helpers for building dashboard-ready ATTPLANE tables.

Use this module after cleaning and enrichment.

The main table here is a flight-level dashboard table:
- one row per flight occurrence
- route details joined by ``route_code``
- aircraft details joined by ``airplane``
- origin and destination airport details joined by airport code
"""

from __future__ import annotations

import polars as pl

from src.data_enrich import (
    enrich_airplanes,
    enrich_airports,
    enrich_flights,
    enrich_routes,
)


def make_flight_dashboard_table(
    flights: pl.DataFrame,
    routes: pl.DataFrame,
    airplanes: pl.DataFrame,
    airports: pl.DataFrame,
) -> pl.DataFrame:
    """Join enriched tables and keep every column.

    Flights are the main table, so their columns keep their original names.
    Joined table columns get a prefix so the final table is easy to read.
    """
    flights = enrich_flights(flights)
    routes = enrich_routes(routes)
    airplanes = enrich_airplanes(airplanes)
    airports = enrich_airports(airports)

    routes = _prefix_for_join(routes, prefix="route_", join_column="route_code")
    dashboard = flights.join(
        routes,
        left_on="route_code",
        right_on="_join_key",
        how="left",
    )

    airplanes = _prefix_for_join(
        airplanes,
        prefix="airplane_",
        join_column="aircraft_registration",
    )
    dashboard = dashboard.join(
        airplanes,
        left_on="airplane",
        right_on="_join_key",
        how="left",
    )

    origin_airports = _prefix_for_join(
        airports,
        prefix="origin_",
        join_column="iata_code",
    )
    dashboard = dashboard.join(
        origin_airports,
        left_on="route_origin",
        right_on="_join_key",
        how="left",
    )

    destination_airports = _prefix_for_join(
        airports,
        prefix="destination_",
        join_column="iata_code",
    )
    dashboard = dashboard.join(
        destination_airports,
        left_on="route_destination",
        right_on="_join_key",
        how="left",
    )

    if (
        "origin_country" in dashboard.columns
        and "destination_country" in dashboard.columns
    ):
        dashboard = dashboard.with_columns(
            (pl.col("origin_country") == pl.col("destination_country"))
            .alias("is_domestic_route")
        )

    if (
        "origin_continent" in dashboard.columns
        and "destination_continent" in dashboard.columns
    ):
        dashboard = dashboard.with_columns(
            (pl.col("origin_continent") == pl.col("destination_continent"))
            .alias("is_same_continent_route")
        )

    return dashboard


def _prefix_for_join(
    df: pl.DataFrame,
    prefix: str,
    join_column: str,
) -> pl.DataFrame:
    """Add a prefix to every column and keep a simple temporary join key."""
    renamed = df.rename({column: f"{prefix}{column}" for column in df.columns})
    return renamed.with_columns(pl.col(f"{prefix}{join_column}").alias("_join_key"))


def check_one_join(
    left: pl.DataFrame,
    right: pl.DataFrame,
    left_column: str,
    right_column: str,
    join_name: str,
) -> dict[str, int | bool | str]:
    """Check one join key before trusting a joined table."""
    right_key_counts = (
        right.group_by(right_column)
        .agg(pl.len().alias("key_count"))
        .filter(pl.col("key_count") > 1)
    )
    right_keys = right.select(pl.col(right_column).alias(left_column)).unique()

    unmatched_rows = left.join(
        right_keys,
        on=left_column,
        how="anti",
    ).height
    joined_rows = left.join(
        right.select(pl.col(right_column).alias(left_column)),
        on=left_column,
        how="left",
    ).height

    return {
        "join": join_name,
        "left_rows": left.height,
        "joined_rows": joined_rows,
        "unmatched_rows": unmatched_rows,
        "duplicate_right_keys": right_key_counts.height,
        "row_count_ok": joined_rows == left.height,
        "all_keys_matched": unmatched_rows == 0,
    }


def check_flight_dashboard_joins(
    flights: pl.DataFrame,
    routes: pl.DataFrame,
    airplanes: pl.DataFrame,
    airports: pl.DataFrame,
    flight_dashboard_table: pl.DataFrame,
) -> pl.DataFrame:
    """Check the joins used for the flight dashboard table."""
    checks = [
        check_one_join(
            flights,
            routes,
            "route_code",
            "route_code",
            "flights to routes",
        ),
        check_one_join(
            flights,
            airplanes,
            "airplane",
            "aircraft_registration",
            "flights to airplanes",
        ),
        check_one_join(
            routes,
            airports,
            "origin",
            "iata_code",
            "routes to origin airports",
        ),
        check_one_join(
            routes,
            airports,
            "destination",
            "iata_code",
            "routes to destination airports",
        ),
    ]

    checks.append(
        {
            "join": "final flight dashboard table",
            "left_rows": flights.height,
            "joined_rows": flight_dashboard_table.height,
            "unmatched_rows": None,
            "duplicate_right_keys": None,
            "row_count_ok": flight_dashboard_table.height == flights.height,
            "all_keys_matched": None,
        }
    )

    return pl.DataFrame(checks)
