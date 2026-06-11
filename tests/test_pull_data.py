"""Tests for src/pull_data.py and src/db.py.

Run unit tests (no DB required):
    pytest tests/test_pull_data.py

Run everything including live-DB2 integration tests:
    pytest tests/test_pull_data.py --integration
"""

from __future__ import annotations

import pathlib
from unittest.mock import MagicMock, patch

import polars as pl
from polars.testing import assert_frame_equal
import pytest

from src.db import DatabaseConfig, build_connection_string
from src.pull_data import (
    CHUNK_SIZE,
    DEFAULT_CONFIG,
    RAW_DIR,
    SCHEMA,
    TABLES,
    pull_all_tables,
    pull_and_save,
    save_tables,
)


# ── Constants ────────────────────────────────────────────────────────────────

class TestConstants:
    def test_exactly_six_tables(self):
        assert len(TABLES) == 6

    def test_all_expected_tables_present(self):
        expected = {
            "AIRPLANES", "AIRPORTS", "FLIGHTS",
            "PASSENGERS", "ROUTES", "TICKETS",
        }
        assert set(TABLES) == expected

    def test_schema_is_attgrp8(self):
        assert SCHEMA == "ATTGRP8"

    def test_raw_dir_is_under_data(self):
        assert RAW_DIR.name == "raw"
        assert RAW_DIR.parent.name == "data"


# ── DatabaseConfig & connection string ───────────────────────────────────────

class TestDatabaseConfig:
    def test_default_config_host(self):
        assert DEFAULT_CONFIG.host == "52.211.123.34"

    def test_default_config_port(self):
        assert DEFAULT_CONFIG.port == 25010

    def test_default_config_database(self):
        assert DEFAULT_CONFIG.name == "ATTPLANE"

    def test_default_config_username(self):
        assert DEFAULT_CONFIG.username == "attgrp8"

    def test_build_connection_string_contains_all_fields(self):
        cfg = DatabaseConfig(
            host="myhost", port=1234, name="MYDB",
            username="user1", password="secret",
        )
        cs = build_connection_string(cfg)
        assert "HOSTNAME=myhost" in cs
        assert "PORT=1234" in cs
        assert "DATABASE=MYDB" in cs
        assert "UID=user1" in cs
        assert "PWD=secret" in cs

    def test_build_connection_string_uppercases_schema(self):
        cfg = DatabaseConfig(
            host="h", port=1, name="D", username="attgrp8", password="p"
        )
        cs = build_connection_string(cfg)
        assert "CURRENTSCHEMA=ATTGRP8" in cs

    def test_config_is_immutable(self):
        with pytest.raises(Exception):
            DEFAULT_CONFIG.host = "other"  # type: ignore[misc]


# ── save_tables ──────────────────────────────────────────────────────────────

class TestSaveTables:
    def test_creates_one_parquet_per_table(self, tmp_path: pathlib.Path):
        tables = {
            "AIRPLANES": pl.DataFrame({"reg": ["G-ABCD"], "model": ["A320"]}),
            "AIRPORTS": pl.DataFrame({"iata": ["MAD", "JFK"]}),
        }
        save_tables(tables, tmp_path)
        assert (tmp_path / "airplanes.parquet").exists()
        assert (tmp_path / "airports.parquet").exists()

    def test_filenames_are_lowercased(self, tmp_path: pathlib.Path):
        import os
        df = pl.DataFrame({"route_code": ["RT01"]})
        save_tables({"ROUTES": df}, tmp_path)
        # os.listdir returns the real on-disk name (preserves case on NTFS).
        actual_names = os.listdir(tmp_path)
        assert "routes.parquet" in actual_names

    def test_parquet_roundtrip_preserves_data(self, tmp_path: pathlib.Path):
        original = pl.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "c"]})
        save_tables({"FLIGHTS": original}, tmp_path)
        reloaded = pl.read_parquet(tmp_path / "flights.parquet")
        assert_frame_equal(reloaded, original)

    def test_creates_missing_output_dir(self, tmp_path: pathlib.Path):
        nested = tmp_path / "does" / "not" / "exist"
        save_tables({"TICKETS": pl.DataFrame({"ticket_id": [1]})}, nested)
        assert nested.exists()
        assert (nested / "tickets.parquet").exists()

    def test_all_six_tables_saved(self, tmp_path: pathlib.Path):
        tables = {name: pl.DataFrame({"x": [1]}) for name in TABLES}
        save_tables(tables, tmp_path)
        for name in TABLES:
            assert (tmp_path / f"{name.lower()}.parquet").exists()

    def test_empty_dataframe_saved(self, tmp_path: pathlib.Path):
        empty = pl.DataFrame({"col": pl.Series([], dtype=pl.Int64)})
        save_tables({"PASSENGERS": empty}, tmp_path)
        reloaded = pl.read_parquet(tmp_path / "passengers.parquet")
        assert len(reloaded) == 0


# ── pull_all_tables ──────────────────────────────────────────────────────────

class TestPullAllTables:
    @patch("src.pull_data.read_table")
    @patch("src.pull_data.get_engine")
    def test_returns_dict_with_all_six_keys(self, mock_engine, mock_read):
        mock_read.return_value = pl.DataFrame({"col": [1]})
        result = pull_all_tables()
        assert set(result.keys()) == set(TABLES)

    @patch("src.pull_data.read_table")
    @patch("src.pull_data.get_engine")
    def test_calls_read_table_once_per_table(self, mock_engine, mock_read):
        mock_read.return_value = pl.DataFrame({"col": [1]})
        pull_all_tables()
        assert mock_read.call_count == len(TABLES)

    @patch("src.pull_data.read_table")
    @patch("src.pull_data.get_engine")
    def test_passes_correct_schema_to_read_table(self, mock_engine, mock_read):
        mock_read.return_value = pl.DataFrame({"col": [1]})
        pull_all_tables()
        for c in mock_read.call_args_list:
            assert c.args[2] == SCHEMA

    @patch("src.pull_data.read_table")
    @patch("src.pull_data.get_engine")
    def test_passes_engine_to_read_table(self, mock_engine, mock_read):
        fake_engine = MagicMock()
        mock_engine.return_value = fake_engine
        mock_read.return_value = pl.DataFrame({"col": [1]})
        pull_all_tables()
        for c in mock_read.call_args_list:
            assert c.args[0] is fake_engine

    @patch("src.pull_data.read_table")
    @patch("src.pull_data.get_engine")
    def test_values_are_polars_dataframes(self, mock_engine, mock_read):
        mock_read.return_value = pl.DataFrame({"col": [1]})
        result = pull_all_tables()
        for df in result.values():
            assert isinstance(df, pl.DataFrame)

    @patch("src.pull_data.read_table")
    @patch("src.pull_data.get_engine")
    def test_uses_provided_config(self, mock_engine, mock_read):
        mock_read.return_value = pl.DataFrame({"col": [1]})
        custom = DatabaseConfig(
            host="x", port=9999, name="DB", username="u", password="p"
        )
        pull_all_tables(config=custom)
        mock_engine.assert_called_once_with(custom)


# ── pull_and_save ────────────────────────────────────────────────────────────


class TestPullAndSave:
    @patch("src.pull_data.stream_table_to_parquet")
    @patch("src.pull_data.get_engine")
    def test_streams_all_tables_when_none_exist(
        self, mock_engine, mock_stream, tmp_path: pathlib.Path
    ):
        mock_stream.return_value = 100
        pull_and_save(output_dir=tmp_path)
        assert mock_stream.call_count == len(TABLES)

    @patch("src.pull_data.stream_table_to_parquet")
    @patch("src.pull_data.get_engine")
    def test_skips_existing_parquet_files(
        self, mock_engine, mock_stream, tmp_path: pathlib.Path
    ):
        for name in ["AIRPLANES", "AIRPORTS", "ROUTES"]:
            pl.DataFrame({"x": [1]}).write_parquet(
                tmp_path / f"{name.lower()}.parquet"
            )
        mock_stream.return_value = 10
        pull_and_save(output_dir=tmp_path)
        assert mock_stream.call_count == len(TABLES) - 3

    @patch("src.pull_data.stream_table_to_parquet")
    @patch("src.pull_data.get_engine")
    def test_no_db_connection_when_all_exist(
        self, mock_engine, mock_stream, tmp_path: pathlib.Path
    ):
        for name in TABLES:
            pl.DataFrame({"x": [1]}).write_parquet(
                tmp_path / f"{name.lower()}.parquet"
            )
        pull_and_save(output_dir=tmp_path)
        mock_engine.assert_not_called()
        mock_stream.assert_not_called()

    @patch("src.pull_data.stream_table_to_parquet")
    @patch("src.pull_data.get_engine")
    def test_returns_path_for_every_table(
        self, mock_engine, mock_stream, tmp_path: pathlib.Path
    ):
        mock_stream.return_value = 10
        result = pull_and_save(output_dir=tmp_path)
        assert set(result.keys()) == set(TABLES)
        for name, path in result.items():
            assert path == tmp_path / f"{name.lower()}.parquet"

    @patch("src.pull_data.stream_table_to_parquet")
    @patch("src.pull_data.get_engine")
    def test_uses_chunk_size_constant(
        self, mock_engine, mock_stream, tmp_path: pathlib.Path
    ):
        mock_stream.return_value = 10
        pull_and_save(output_dir=tmp_path)
        for c in mock_stream.call_args_list:
            assert c.args[4] == CHUNK_SIZE

    @patch("src.pull_data.stream_table_to_parquet")
    @patch("src.pull_data.get_engine")
    def test_passes_custom_config_to_engine(
        self, mock_engine, mock_stream, tmp_path: pathlib.Path
    ):
        mock_stream.return_value = 10
        custom = DatabaseConfig(
            host="x", port=1, name="D", username="u", password="p"
        )
        pull_and_save(config=custom, output_dir=tmp_path)
        mock_engine.assert_called_once_with(custom)


# ── Integration tests (require live DB2) ────────────────────────────────────

@pytest.mark.integration
class TestIntegration:
    """Skipped by default. Run with: pytest --integration"""

    def test_pull_all_tables_returns_six_dataframes(self):
        tables = pull_all_tables()
        assert set(tables.keys()) == set(TABLES)
        for name, df in tables.items():
            assert isinstance(df, pl.DataFrame), f"{name} is not a DataFrame"
            assert len(df) > 0, f"{name} returned 0 rows"

    def test_column_names_are_lowercase(self):
        tables = pull_all_tables()
        for name, df in tables.items():
            for col in df.columns:
                assert col == col.lower(), f"{name}.{col} is not lowercase"

    def test_airplanes_has_expected_columns(self):
        tables = pull_all_tables()
        df = tables["AIRPLANES"]
        for col in ("aircraft_registration", "model"):
            assert col in df.columns, f"Missing column {col} in AIRPLANES"

    def test_airports_has_expected_columns(self):
        tables = pull_all_tables()
        df = tables["AIRPORTS"]
        for col in ("iata_code", "city", "country"):
            assert col in df.columns, f"Missing column {col} in AIRPORTS"

    def test_flights_has_expected_columns(self):
        tables = pull_all_tables()
        df = tables["FLIGHTS"]
        for col in ("flight_id", "route_code", "departure"):
            assert col in df.columns, f"Missing column {col} in FLIGHTS"

    def test_passengers_has_expected_columns(self):
        tables = pull_all_tables()
        df = tables["PASSENGERS"]
        for col in ("id", "country"):
            assert col in df.columns, f"Missing column {col} in PASSENGERS"

    def test_routes_has_expected_columns(self):
        tables = pull_all_tables()
        df = tables["ROUTES"]
        for col in ("route_code", "origin", "destination", "distance"):
            assert col in df.columns, f"Missing column {col} in ROUTES"

    def test_tickets_has_expected_columns(self):
        tables = pull_all_tables()
        df = tables["TICKETS"]
        for col in ("ticket_id", "passenger_id", "flight_id", "total_amount"):
            assert col in df.columns, f"Missing column {col} in TICKETS"

    def test_save_and_reload_roundtrip(self, tmp_path: pathlib.Path):
        tables = pull_all_tables()
        save_tables(tables, tmp_path)
        for name in TABLES:
            path = tmp_path / f"{name.lower()}.parquet"
            assert path.exists(), f"Missing {path}"
            reloaded = pl.read_parquet(path)
            assert_frame_equal(
                reloaded, tables[name]
            )

    def test_pull_and_save_writes_all_parquet_files(
        self, tmp_path: pathlib.Path
    ):
        pull_and_save(output_dir=tmp_path)
        for name in TABLES:
            assert (tmp_path / f"{name.lower()}.parquet").exists()
