"""Analytical aggregations and business metric helpers.

Cleaning belongs in ``src.data_clean``. Feature engineering and joined modeling
tables belong in ``src.data_enrich``. Keep this module for actual analysis:
route revenue, fleet utilization summaries, passenger segments, and dashboard
metric tables.
"""

from __future__ import annotations

import polars as pl

from src import config

# Reference year for aircraft age, matching the project's existing convention.
AGE_REFERENCE_YEAR = config.AGE_REFERENCE_YEAR


def build_metrics_placeholder(df: pl.DataFrame) -> pl.DataFrame:
    """Placeholder for route, revenue, fleet, or passenger metrics."""
    raise NotImplementedError("Implement analytics logic here.")
