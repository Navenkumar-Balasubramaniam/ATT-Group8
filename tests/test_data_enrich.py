"""Tests for table enrichment helpers."""

from __future__ import annotations

from datetime import date, datetime

import polars as pl

from src.data_enrich import (
    enrich_airplanes,
    enrich_airports,
    enrich_flights,
    enrich_passengers,
    enrich_routes,
    enrich_tables,
)


def test_enrich_flights_adds_time_features():
    flights = pl.DataFrame(
        {
            "departure": [datetime(2020, 1, 4, 8, 30)],
            "arrival": [datetime(2020, 1, 4, 10, 0)],
        }
    )

    enriched = enrich_flights(flights)

    assert enriched["departure_year"].item() == 2020
    assert enriched["departure_hour"].item() == 8
    assert enriched["is_weekend"].item() is True
    assert enriched["scheduled_duration_minutes"].item() == 90


def test_enrich_airplanes_adds_capacity_features():
    airplanes = pl.DataFrame(
        {
            "model": ["Airbus A320"],
            "seats_business": [8],
            "seats_premium": [12],
            "seats_economy": [120],
        }
    )

    enriched = enrich_airplanes(airplanes)

    assert enriched["total_seats"].item() == 140
    assert enriched["has_business_class"].item() is True
    assert enriched["has_premium_class"].item() is True
    assert enriched["model_family"].item() == "Airbus"


def test_enrich_routes_adds_route_features():
    routes = pl.DataFrame(
        {
            "distance": [900, 2_500, 6_000, 9_000],
            "flight_minutes": [60, 180, 420, 600],
            "parent_route": [None, "R1", None, None],
        }
    )

    enriched = enrich_routes(routes)

    assert enriched["distance_band"].to_list() == [
        "short",
        "medium",
        "long",
        "very long",
    ]
    assert enriched["flight_hours"].to_list()[0] == 1
    assert enriched["average_speed"].to_list()[0] == 900
    assert enriched["has_parent_route"].to_list() == [False, True, False, False]


def test_enrich_airports_adds_display_features():
    airports = pl.DataFrame(
        {
            "iata_code": ["MAD"],
            "city": ["Madrid"],
            "latitude": [40.5],
            "longitude": [-3.6],
            "airport_tax": [25.0],
        }
    )

    enriched = enrich_airports(airports)

    assert enriched["airport_label"].item() == "Madrid (MAD)"
    assert enriched["has_coordinates"].item() is True
    assert enriched["airport_tax_band"].item() == "medium"


def test_enrich_passengers_adds_age_and_vip_features():
    passengers = pl.DataFrame(
        {
            "birth_date": [date(1990, 6, 1)],
            "vipcard": ["VIP-123"],
        }
    )

    enriched = enrich_passengers(
        passengers,
        reference_date=date(2025, 6, 1),
    )

    assert enriched["age_years"].item() == 35
    assert enriched["age_group"].item() == "35-54"
    assert enriched["has_vip_card"].item() is True


def test_enrich_tables_applies_matching_enrichers():
    tables = {
        "airplanes_clean": pl.DataFrame(
            {
                "seats_business": [1],
                "seats_premium": [2],
                "seats_economy": [3],
            }
        ),
        "unknown_clean": pl.DataFrame({"x": [1]}),
    }

    enriched = enrich_tables(tables)

    assert "airplanes" in enriched
    assert "unknown" in enriched
    assert enriched["airplanes"]["total_seats"].item() == 6
    assert enriched["unknown"]["x"].item() == 1
