"""Tests for the simple data cleaning helpers."""

from __future__ import annotations

import polars as pl

from src.data_clean import clean_dataframe, clean_missing_values, parse_dates


def test_clean_missing_values_trims_text_and_sets_placeholders_to_null():
    raw = pl.DataFrame({"city": [" Madrid ", "", " N/A ", "null"]})

    cleaned = clean_missing_values(raw)

    assert cleaned["city"].to_list() == ["Madrid", None, None, None]


def test_parse_dates_converts_selected_columns():
    raw = pl.DataFrame(
        {
            "birth_date": ["1990-01-01", "not a date"],
            "departure": ["2020-01-01 08:30:00", "bad datetime"],
        }
    )

    cleaned = parse_dates(
        raw,
        date_columns=("birth_date",),
        datetime_columns=("departure",),
    )

    assert cleaned.schema["birth_date"] == pl.Date
    assert cleaned.schema["departure"].base_type() == pl.Datetime
    assert cleaned["birth_date"].null_count() == 1
    assert cleaned["departure"].null_count() == 1


def test_clean_dataframe_keeps_column_names_and_drops_exact_duplicates():
    raw = pl.DataFrame(
        {
            " Aircraft Registration ": [" ie123 ", " ie123 "],
            "Build Date": ["2020-01-01", "2020-01-01"],
            "Notes": [" N/A ", " N/A "],
        }
    )

    cleaned = clean_dataframe(raw, date_columns=("Build Date",))

    assert cleaned.height == 1
    assert cleaned.columns == [" Aircraft Registration ", "Build Date", "Notes"]
    assert cleaned[" Aircraft Registration "].item() == "ie123"
    assert cleaned["Notes"].item() is None
    assert cleaned.schema["Build Date"] == pl.Date
