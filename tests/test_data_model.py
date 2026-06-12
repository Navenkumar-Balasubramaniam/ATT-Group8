"""Tests for joined dashboard table helpers."""

from __future__ import annotations

from datetime import datetime

import polars as pl

from src.data_model import (
    check_flight_dashboard_joins,
    check_one_join,
    make_flight_dashboard_table,
)


def test_make_flight_dashboard_table_joins_expected_columns():
    flights = pl.DataFrame(
        {
            "flight_id": ["F1"],
            "route_code": ["R1"],
            "airplane": ["A1"],
            "departure": [datetime(2020, 1, 4, 8, 30)],
            "arrival": [datetime(2020, 1, 4, 10, 0)],
        }
    )
    routes = pl.DataFrame(
        {
            "route_code": ["R1"],
            "origin": ["MAD"],
            "destination": ["BCN"],
            "parent_route": ["ROOT"],
            "leg_number": [1],
            "distance": [500],
            "flight_minutes": [90],
        }
    )
    airplanes = pl.DataFrame(
        {
            "aircraft_registration": ["A1"],
            "model": ["Airbus A320"],
            "seats_business": [8],
            "seats_premium": [12],
            "seats_economy": [120],
            "crew_members": [6],
        }
    )
    airports = pl.DataFrame(
        {
            "iata_code": ["MAD", "BCN"],
            "city": ["Madrid", "Barcelona"],
            "country": ["Spain", "Spain"],
            "continent": ["Europe", "Europe"],
            "latitude": [40.5, 41.3],
            "longitude": [-3.6, 2.1],
            "airport_tax": [25.0, 30.0],
        }
    )

    dashboard = make_flight_dashboard_table(
        flights,
        routes,
        airplanes,
        airports,
    )

    assert dashboard.height == flights.height
    assert dashboard["route_distance_band"].item() == "short"
    assert dashboard["route_parent_route"].item() == "ROOT"
    assert dashboard["airplane_model_family"].item() == "Airbus"
    assert dashboard["airplane_crew_members"].item() == 6
    assert dashboard["origin_city"].item() == "Madrid"
    assert dashboard["destination_city"].item() == "Barcelona"
    assert dashboard["origin_iata_code"].item() == "MAD"
    assert dashboard["destination_iata_code"].item() == "BCN"
    assert dashboard["is_domestic_route"].item() is True


def test_check_flight_dashboard_joins_reports_row_counts_and_matches():
    flights = pl.DataFrame({"route_code": ["R1"], "airplane": ["A1"]})
    routes = pl.DataFrame(
        {
            "route_code": ["R1"],
            "origin": ["MAD"],
            "destination": ["BCN"],
        }
    )
    airplanes = pl.DataFrame({"aircraft_registration": ["A1"]})
    airports = pl.DataFrame({"iata_code": ["MAD", "BCN"]})
    dashboard = make_flight_dashboard_table(flights, routes, airplanes, airports)

    checks = check_flight_dashboard_joins(
        flights,
        routes,
        airplanes,
        airports,
        dashboard,
    )

    assert checks["row_count_ok"].to_list() == [True, True, True, True, True]
    assert checks["all_keys_matched"].drop_nulls().to_list() == [
        True,
        True,
        True,
        True,
    ]


def test_check_one_join_finds_unmatched_and_duplicate_keys():
    left = pl.DataFrame({"route_code": ["R1", "R2"]})
    right = pl.DataFrame({"route_code": ["R1", "R1"]})

    result = check_one_join(
        left,
        right,
        "route_code",
        "route_code",
        "test join",
    )

    assert result["left_rows"] == 2
    assert result["joined_rows"] == 3
    assert result["unmatched_rows"] == 1
    assert result["duplicate_right_keys"] == 1
    assert result["row_count_ok"] is False
    assert result["all_keys_matched"] is False
