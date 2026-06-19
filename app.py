"""ATT Plane Analytics -- Streamlit dashboard.

Reads only the small, pre-built parquet files described in the data contract
(``docs/data_contract.md`` / ``src/contracts.py``). It never connects to DB2 and
never touches the 248M-row tickets table at runtime.

Build the data first (one-time, no database needed):

    uv run python scripts/build_dashboard_data.py

Then run the app:

    uv run streamlit run app.py
"""

from __future__ import annotations

import polars as pl
import plotly.express as px
import streamlit as st

from src import analysis, config, contracts

st.set_page_config(page_title=config.APP_TITLE, layout=config.APP_LAYOUT)

# Master columns used as filter dimensions (prefixed during the join).
CONTINENT_COL = "origin_continent"
DISTANCE_BAND_COL = "route_distance_band"
MODEL_FAMILY_COL = "airplane_model_family"

# Files the app cannot run without.
REQUIRED_FILES = {
    "master": contracts.MASTER_FILE,
    "revenue_by_route": contracts.OUTPUT_FILES["revenue_by_route"],
    "revenue_by_month": contracts.OUTPUT_FILES["revenue_by_month"],
    "revenue_by_class": contracts.OUTPUT_FILES["revenue_by_class"],
}


@st.cache_data
def load_master() -> pl.DataFrame:
    return pl.read_parquet(contracts.MASTER_FILE)


@st.cache_data
def load_output(name: str) -> pl.DataFrame:
    return pl.read_parquet(contracts.OUTPUT_FILES[name])


def options_for(df: pl.DataFrame, column: str) -> list[str]:
    """Sorted, non-null distinct values for a filter dropdown."""
    if column not in df.columns:
        return []
    return df.select(pl.col(column).drop_nulls().unique().sort()).to_series().to_list()


def apply_filter(df: pl.DataFrame, column: str, value: str | None) -> pl.DataFrame:
    if not value or value == "All" or column not in df.columns:
        return df
    return df.filter(pl.col(column) == value)


# --------------------------------------------------------------------------- #
# Guard: make sure the prepared data exists.
# --------------------------------------------------------------------------- #
missing = contracts.missing_files(REQUIRED_FILES)
if missing:
    st.title(config.APP_TITLE)
    st.error(
        "Prepared data is missing: "
        + ", ".join(missing)
        + ".\n\nBuild it first (no database needed):\n\n"
        "```bash\nuv run python scripts/build_dashboard_data.py\n```"
    )
    st.stop()


# --------------------------------------------------------------------------- #
# Load + filters
# --------------------------------------------------------------------------- #
master = load_master()

st.sidebar.header("Filters")
continent = st.sidebar.selectbox("Origin continent", ["All"] + options_for(master, CONTINENT_COL))
distance_band = st.sidebar.selectbox("Distance band", ["All"] + options_for(master, DISTANCE_BAND_COL))
model_family = st.sidebar.selectbox("Aircraft model family", ["All"] + options_for(master, MODEL_FAMILY_COL))
top_n = st.sidebar.slider("Top N", min_value=5, max_value=30, value=10)

filtered = apply_filter(master, CONTINENT_COL, continent)
filtered = apply_filter(filtered, DISTANCE_BAND_COL, distance_band)
filtered = apply_filter(filtered, MODEL_FAMILY_COL, model_family)

active_filters = [
    label
    for label, value in (
        ("continent", continent),
        ("distance", distance_band),
        ("fleet", model_family),
    )
    if value != "All"
]

st.title(config.APP_TITLE)
st.caption(
    "Flight, fleet and revenue overview for the ATTPLANE network. "
    + ("Filters active: " + ", ".join(active_filters) if active_filters else "Showing all flights.")
)

if filtered.height == 0:
    st.warning("No flights match the current filters. Try widening them.")
    st.stop()


# --------------------------------------------------------------------------- #
# Overview KPIs
# --------------------------------------------------------------------------- #
# Revenue responds to filters by restricting to the routes still in view.
visible_routes = filtered.select(pl.col("route_code").unique()).to_series().to_list()
revenue_route = load_output("revenue_by_route").filter(pl.col("route_code").is_in(visible_routes))

top_route_row = (
    filtered.group_by("route_code").agg(pl.len().alias("n")).sort("n", descending=True).head(1)
)
top_route = top_route_row.item(0, "route_code") if top_route_row.height else "-"

top_continent_row = analysis.flights_by_continent(filtered).head(1)
top_continent = top_continent_row.item(0, "origin_continent") if top_continent_row.height else "-"

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Flights", f"{filtered.height:,}")
k2.metric("Total revenue", f"${revenue_route['total_revenue'].sum():,.0f}")
k3.metric("Tickets", f"{revenue_route['n_tickets'].sum():,}")
k4.metric("Aircraft in view", f"{filtered['airplane'].n_unique():,}")
k5.metric("Top route", top_route)


# --------------------------------------------------------------------------- #
# Section 1 -- Route performance
# --------------------------------------------------------------------------- #
st.subheader("Route performance")
col_a, col_b = st.columns(2)

routes_ranked = analysis.flights_by_route(filtered).head(top_n).with_columns(
    (pl.col("route_origin") + " -> " + pl.col("route_destination")).alias("route")
)
fig_routes = px.bar(
    routes_ranked.sort("total_flights"),
    x="total_flights",
    y="route",
    orientation="h",
    title=f"Top {top_n} routes by flights",
    labels={"total_flights": "Flights", "route": "Route"},
)
col_a.plotly_chart(fig_routes, width="stretch")

continent_volume = analysis.flights_by_continent(filtered)
fig_continent = px.bar(
    continent_volume.sort("total_flights", descending=True),
    x="origin_continent",
    y="total_flights",
    title="Flights by origin continent",
    labels={"origin_continent": "Continent", "total_flights": "Flights"},
)
col_b.plotly_chart(fig_continent, width="stretch")


# --------------------------------------------------------------------------- #
# Section 2 -- Fleet utilization
# --------------------------------------------------------------------------- #
st.subheader("Fleet utilization")
col_c, col_d = st.columns(2)

fleet = analysis.fleet_usage(filtered).head(top_n)
fig_fleet = px.bar(
    fleet.sort("total_flights"),
    x="total_flights",
    y="airplane",
    orientation="h",
    title=f"Top {top_n} aircraft by flights",
    labels={"total_flights": "Flights", "airplane": "Aircraft"},
    hover_data=["airplane_model", "total_distance_km"],
)
col_c.plotly_chart(fig_fleet, width="stretch")

maintenance = analysis.fleet_maintenance(filtered)
fig_maint = px.scatter(
    maintenance,
    x="aircraft_age_years",
    y="airplane_maintenance_flight_hours",
    color="airplane_model",
    title="Aircraft age vs maintenance flight hours",
    labels={
        "aircraft_age_years": "Aircraft age (years)",
        "airplane_maintenance_flight_hours": "Maintenance flight hours",
        "airplane_model": "Model",
    },
    hover_data=["airplane"],
)
fig_maint.update_layout(showlegend=False)
col_d.plotly_chart(fig_maint, width="stretch")


# --------------------------------------------------------------------------- #
# Section 3 -- Revenue
# --------------------------------------------------------------------------- #
st.subheader("Revenue")
if revenue_route.height == 0:
    st.info("No ticket revenue for the routes in the current filter.")
else:
    col_e, col_f = st.columns(2)

    revenue_top = revenue_route.sort("total_revenue", descending=True).head(top_n).with_columns(
        (pl.col("route_origin") + " -> " + pl.col("route_destination")).alias("route")
    )
    fig_rev_route = px.bar(
        revenue_top.sort("total_revenue"),
        x="total_revenue",
        y="route",
        orientation="h",
        title=f"Top {top_n} routes by revenue (filtered)",
        labels={"total_revenue": "Revenue ($)", "route": "Route"},
        hover_data=["n_tickets", "avg_ticket_price"],
    )
    col_e.plotly_chart(fig_rev_route, width="stretch")

    revenue_month = load_output("revenue_by_month").with_columns(
        pl.date(pl.col("year"), pl.col("month"), 1).alias("period")
    )
    fig_rev_month = px.line(
        revenue_month.sort("period"),
        x="period",
        y="total_revenue",
        title="Monthly revenue (all tickets)",
        labels={"period": "Month", "total_revenue": "Revenue ($)"},
        markers=True,
    )
    col_f.plotly_chart(fig_rev_month, width="stretch")

    st.markdown("**Revenue by cabin class (all tickets)**")
    st.dataframe(
        load_output("revenue_by_class").sort("total_revenue", descending=True),
        width="stretch",
    )


# --------------------------------------------------------------------------- #
# Data preview
# --------------------------------------------------------------------------- #
with st.expander("Route revenue detail (filtered)"):
    st.dataframe(
        revenue_route.sort("total_revenue", descending=True).head(100),
        width="stretch",
    )
