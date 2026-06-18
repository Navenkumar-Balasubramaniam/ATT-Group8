"""Beginner-friendly feature engineering helpers for ATTPLANE tables.

Cleaning makes data usable.
Enrichment adds useful business columns for analysis and dashboards.

Each function below takes one Polars DataFrame and returns that same table with
extra columns added. The functions are allowed to know column names because
enrichment is business logic.
"""

from __future__ import annotations

from datetime import date

import polars as pl


def enrich_flights(flights: pl.DataFrame) -> pl.DataFrame:
    """Add simple time features to the flights table."""
    has_departure_datetime = (
        "departure" in flights.columns
        and flights.schema["departure"].base_type() == pl.Datetime
    )
    has_arrival_datetime = (
        "arrival" in flights.columns
        and flights.schema["arrival"].base_type() == pl.Datetime
    )

    if has_departure_datetime:
        flights = flights.with_columns(
            pl.col("departure").dt.date().alias("departure_date"),
            pl.col("departure").dt.year().alias("departure_year"),
            pl.col("departure").dt.month().alias("departure_month"),
            pl.col("departure").dt.weekday().alias("departure_weekday"),
            pl.col("departure").dt.hour().alias("departure_hour"),
            (pl.col("departure").dt.weekday() >= 6).alias("is_weekend"),
        )

    if has_departure_datetime and has_arrival_datetime:
        flights = flights.with_columns(
            (pl.col("arrival") - pl.col("departure"))
            .dt.total_minutes()
            .alias("scheduled_duration_minutes")
        )

    return flights


def enrich_airplanes(airplanes: pl.DataFrame) -> pl.DataFrame:
    """Add simple capacity features to the airplanes table."""
    seat_columns = ["seats_business", "seats_premium", "seats_economy"]
    available_seat_columns = [
        column for column in seat_columns if column in airplanes.columns
    ]

    if available_seat_columns:
        airplanes = airplanes.with_columns(
            pl.sum_horizontal(
                [pl.col(column).fill_null(0) for column in available_seat_columns]
            ).alias("total_seats")
        )

    if "seats_business" in airplanes.columns:
        airplanes = airplanes.with_columns(
            (pl.col("seats_business").fill_null(0) > 0)
            .alias("has_business_class")
        )

    if "seats_premium" in airplanes.columns:
        airplanes = airplanes.with_columns(
            (pl.col("seats_premium").fill_null(0) > 0)
            .alias("has_premium_class")
        )

    if "model" in airplanes.columns:
        model_upper = pl.col("model").cast(pl.String).str.to_uppercase()
        airplanes = airplanes.with_columns(
            pl.when(model_upper.str.contains("AIRBUS"))
            .then(pl.lit("Airbus"))
            .when(model_upper.str.contains("BOEING"))
            .then(pl.lit("Boeing"))
            .otherwise(pl.lit("Other"))
            .alias("model_family")
        )

    return airplanes


def enrich_routes(routes: pl.DataFrame) -> pl.DataFrame:
    """Add simple distance and duration features to the routes table."""
    if "distance" in routes.columns:
        routes = routes.with_columns(
            pl.when(pl.col("distance") < 1_500)
            .then(pl.lit("short"))
            .when(pl.col("distance") < 4_000)
            .then(pl.lit("medium"))
            .when(pl.col("distance") < 8_000)
            .then(pl.lit("long"))
            .otherwise(pl.lit("very long"))
            .alias("distance_band")
        )

    if "flight_minutes" in routes.columns:
        routes = routes.with_columns(
            (pl.col("flight_minutes") / 60).alias("flight_hours")
        )

    if "distance" in routes.columns and "flight_minutes" in routes.columns:
        routes = routes.with_columns(
            pl.when(pl.col("flight_minutes") > 0)
            .then(pl.col("distance") / (pl.col("flight_minutes") / 60))
            .otherwise(None)
            .round(1)
            .alias("average_speed")
        )

    if "parent_route" in routes.columns:
        routes = routes.with_columns(
            pl.col("parent_route").is_not_null().alias("has_parent_route")
        )

    return routes


def enrich_airports(airports: pl.DataFrame) -> pl.DataFrame:
    """Add simple display and tax features to the airports table."""
    if "city" in airports.columns and "iata_code" in airports.columns:
        airports = airports.with_columns(
            (
                pl.col("city").cast(pl.String)
                + pl.lit(" (")
                + pl.col("iata_code").cast(pl.String)
                + pl.lit(")")
            ).alias("airport_label")
        )

    if "latitude" in airports.columns and "longitude" in airports.columns:
        airports = airports.with_columns(
            (
                pl.col("latitude").is_not_null()
                & pl.col("longitude").is_not_null()
            ).alias("has_coordinates")
        )

    if "airport_tax" in airports.columns:
        airports = airports.with_columns(
            pl.when(pl.col("airport_tax") < 20)
            .then(pl.lit("low"))
            .when(pl.col("airport_tax") < 50)
            .then(pl.lit("medium"))
            .otherwise(pl.lit("high"))
            .alias("airport_tax_band")
        )

    return airports


def enrich_passengers(
    passengers: pl.DataFrame,
    *,
    reference_date: date | None = None,
) -> pl.DataFrame:
    """Add simple non-private features to the passengers table."""
    if reference_date is None:
        reference_date = date.today()

    has_birth_date = (
        "birth_date" in passengers.columns
        and passengers.schema["birth_date"] == pl.Date
    )

    if has_birth_date:
        age = (
            (pl.lit(reference_date) - pl.col("birth_date"))
            .dt.total_days()
            / 365.25
        ).floor()

        passengers = passengers.with_columns(
            age.cast(pl.Int64).alias("age_years"),
            pl.when(pl.col("birth_date").is_null())
            .then(None)
            .when(age < 18)
            .then(pl.lit("under 18"))
            .when(age < 35)
            .then(pl.lit("18-34"))
            .when(age < 55)
            .then(pl.lit("35-54"))
            .otherwise(pl.lit("55+"))
            .alias("age_group"),
        )

    if "vipcard" in passengers.columns:
        passengers = passengers.with_columns(
            pl.col("vipcard").is_not_null().alias("has_vip_card")
        )

    return passengers


def enrich_tables(
    tables: dict[str, pl.DataFrame],
    *,
    reference_date: date | None = None,
) -> dict[str, pl.DataFrame]:
    """Enrich every known table in a dictionary of DataFrames."""
    enriched = {}

    for table_name, df in tables.items():
        clean_name = table_name.removesuffix("_clean")

        if clean_name == "airplanes":
            enriched[clean_name] = enrich_airplanes(df)
        elif clean_name == "airports":
            enriched[clean_name] = enrich_airports(df)
        elif clean_name == "flights":
            enriched[clean_name] = enrich_flights(df)
        elif clean_name == "passengers":
            enriched[clean_name] = enrich_passengers(
                df,
                reference_date=reference_date,
            )
        elif clean_name == "routes":
            enriched[clean_name] = enrich_routes(df)
        else:
            enriched[clean_name] = df

    return enriched
