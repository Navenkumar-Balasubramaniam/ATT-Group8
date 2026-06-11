"""Data cleaning, joins, feature engineering, and analytics helpers.

This module should own the reusable Polars transformations used by the notebook and app.
"""

from __future__ import annotations

import polars as pl


def clean_columns_placeholder(df: pl.DataFrame) -> pl.DataFrame:
    """Placeholder for standardizing column names and data types."""
    raise NotImplementedError("Implement cleaning logic here.")


def build_metrics_placeholder(df: pl.DataFrame) -> pl.DataFrame:
    """Placeholder for route, revenue, fleet, or passenger metrics."""
    raise NotImplementedError("Implement analytics logic here.")
