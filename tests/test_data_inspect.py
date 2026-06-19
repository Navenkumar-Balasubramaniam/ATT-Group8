"""Tests for simple data inspection helpers."""

from __future__ import annotations

import polars as pl

from src.data_inspect import (
    check_raw_files,
    load_tables,
    missing_value_counts,
    summary_statistics,
)


def test_check_raw_files_reports_ok_and_missing(tmp_path):
    pl.DataFrame({"x": [1, 2]}).write_parquet(tmp_path / "airplanes.parquet")

    result = check_raw_files(
        raw_dir=tmp_path,
        table_names=("airplanes", "tickets"),
    )

    status_by_table = {
        row["table"]: row["status"]
        for row in result.to_dicts()
    }
    assert status_by_table == {
        "airplanes": "ok",
        "tickets": "missing",
    }


def test_load_tables_returns_dictionary_of_dataframes(tmp_path):
    pl.DataFrame({"x": [1, 2, 3]}).write_parquet(tmp_path / "airplanes.parquet")

    tables = load_tables(
        data_dir=tmp_path,
        table_names=("airplanes",),
        sample_rows=2,
    )

    assert list(tables) == ["airplanes"]
    assert tables["airplanes"].height == 2


def test_summary_statistics_reports_numeric_columns():
    tables = {
        "passengers": pl.DataFrame(
            {"age": [20, 30, 40], "country": ["ES", "FR", "ES"]}
        )
    }

    summary = summary_statistics(tables)
    age_row = summary.filter(pl.col("column") == "age").to_dicts()[0]

    assert age_row["min"] == 20
    assert age_row["mean"] == 30
    assert age_row["median"] == 30
    assert age_row["max"] == 40


def test_missing_value_counts_reports_nulls_and_blank_strings():
    tables = {
        "passengers": pl.DataFrame(
            {"country": ["ES", None, " "], "age": [20, 30, None]}
        )
    }

    missing = missing_value_counts(tables)
    country_row = missing.filter(pl.col("column") == "country").to_dicts()[0]
    age_row = missing.filter(pl.col("column") == "age").to_dicts()[0]

    assert country_row["null_count"] == 1
    assert country_row["blank_string_count"] == 1
    assert country_row["missing_count"] == 2
    assert age_row["missing_count"] == 1
