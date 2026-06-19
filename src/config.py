"""Central configuration for the ATTPLANE project.

Every hardcoded value the pipeline relies on lives here so paths, database
credentials, table names, and the business thresholds used during cleaning and
enrichment are defined in exactly one place. Other modules import from this file
instead of repeating literals.

This module intentionally depends on nothing else in the project (only the
standard library) so it can be imported from anywhere without circular imports.

Note on responsibilities:

- ``src.config``    -> primitive constants (paths, DB, table names, thresholds).
- ``src.contracts`` -> the input/output *file* and *column* contract, built on
  top of the directories and table names defined here.
"""

from __future__ import annotations

import pathlib

# --------------------------------------------------------------------------- #
# Paths (anchored to the repo root, regardless of where code is run from)
# --------------------------------------------------------------------------- #
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"

# --------------------------------------------------------------------------- #
# Source tables
# --------------------------------------------------------------------------- #
# Logical (lowercase) raw table names, used for parquet file names on disk.
RAW_TABLES: tuple[str, ...] = (
    "airplanes",
    "airports",
    "flights",
    "passengers",
    "routes",
    "tickets",
)

# Tables too large to clean/aggregate eagerly (cleaned via the streaming engine).
STREAMING_TABLES: tuple[str, ...] = ("tickets",)

# Date / datetime columns to parse during cleaning, per table.
DATE_COLUMNS_BY_TABLE: dict[str, tuple[str, ...]] = {
    "airplanes": ("build_date", "maintenance_last_acheck", "maintenance_last_bcheck"),
    "passengers": ("birth_date",),
}
DATETIME_COLUMNS_BY_TABLE: dict[str, tuple[str, ...]] = {
    "flights": ("departure", "arrival"),
    "tickets": ("departure",),
}

# --------------------------------------------------------------------------- #
# Database (course-shared teaching DB2 instance)
# --------------------------------------------------------------------------- #
DB_HOST = "52.211.123.34"
DB_PORT = 25010
DB_NAME = "ATTPLANE"
DB_USERNAME = "attgrp8"
DB_PASSWORD = "bigdata"
DB_SCHEMA = "ATTGRP8"

# Uppercase table names as stored in the DB2 schema (used by the pull step).
DB_TABLES: tuple[str, ...] = tuple(name.upper() for name in RAW_TABLES)

# Rows fetched per batch when streaming a DB2 table to parquet.
DB_CHUNK_SIZE = 50_000

# --------------------------------------------------------------------------- #
# Cleaning
# --------------------------------------------------------------------------- #
# Text values treated as missing (compared case-insensitively, after trimming).
MISSING_TEXT_VALUES: set[str] = {"", "NA", "N/A", "NULL", "NONE", "NAN"}

# Files with more rows than this are cleaned with the streaming engine.
DEFAULT_STREAMING_THRESHOLD_ROWS = 5_000_000

# Formats used to parse date / datetime columns during cleaning.
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S%.f",
)

# --------------------------------------------------------------------------- #
# Enrichment business rules
# --------------------------------------------------------------------------- #
# Route distance bands (km): the label applies when distance < the threshold.
DISTANCE_BAND_SHORT_MAX_KM = 1_500
DISTANCE_BAND_MEDIUM_MAX_KM = 4_000
DISTANCE_BAND_LONG_MAX_KM = 8_000
DISTANCE_BAND_LABELS = ("short", "medium", "long", "very long")

# Airport tax bands: the label applies when airport_tax < the threshold.
AIRPORT_TAX_LOW_MAX = 20
AIRPORT_TAX_MEDIUM_MAX = 50
AIRPORT_TAX_BAND_LABELS = ("low", "medium", "high")

# Passenger age groups (years): the label applies when age < the threshold.
AGE_GROUP_CHILD_MAX = 18
AGE_GROUP_YOUNG_MAX = 35
AGE_GROUP_MID_MAX = 55
AGE_GROUP_LABELS = ("under 18", "18-34", "35-54", "55+")

# Days per year used to convert a birth date into an age.
DAYS_PER_YEAR = 365.25

# Aircraft model family detection: (uppercase keyword, family label) pairs.
MODEL_FAMILY_KEYWORDS = (("AIRBUS", "Airbus"), ("BOEING", "Boeing"))
MODEL_FAMILY_OTHER = "Other"

# Reference year used to compute aircraft age (age = year - build_year).
AGE_REFERENCE_YEAR = 2026

# --------------------------------------------------------------------------- #
# Streamlit app
# --------------------------------------------------------------------------- #
APP_TITLE = "ATT Plane Analytics"
APP_LAYOUT = "wide"
