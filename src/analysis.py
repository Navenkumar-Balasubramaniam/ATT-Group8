"""Analytical aggregations and business metric helpers.

Cleaning belongs in ``src.data_clean``. Feature engineering and joined modeling
tables belong in ``src.data_enrich``. Keep this module for actual analysis:
route revenue, fleet utilization summaries, passenger segments, and dashboard
metric tables.
"""

from __future__ import annotations

import polars as pl


def clean_columns_placeholder(df: pl.DataFrame) -> pl.DataFrame:
    """Compatibility placeholder; use src.data_clean for cleaning logic."""
    raise NotImplementedError("Use src.data_clean for cleaning logic.")


def build_metrics_placeholder(df: pl.DataFrame) -> pl.DataFrame:
    """Placeholder for route, revenue, fleet, or passenger metrics."""
    raise NotImplementedError("Implement analytics logic here.")
