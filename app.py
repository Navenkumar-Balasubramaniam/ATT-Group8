import polars as pl
import plotly.express as px
import streamlit as st

from src import analysis, config, contracts

st.set_page_config(page_title=config.APP_TITLE, layout=config.APP_LAYOUT)

DATA_PATH = "data/main_clean.parquet"


@st.cache_data
def load_data() -> pl.DataFrame:
    return pl.read_parquet(DATA_PATH)


def top_categories(df: pl.DataFrame, category_col: str, top_n: int = 10) -> pl.DataFrame:
    return (
        df
        .lazy()
        .group_by(category_col)
        .agg(pl.len().alias("n_rows"))
        .sort("n_rows", descending=True)
        .head(top_n)
        .collect()
    )


def filter_data(df: pl.DataFrame, selected_value: str | None, category_col: str | None) -> pl.DataFrame:
    if not selected_value or not category_col or selected_value == "All":
        return df


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

df = load_data()

st.sidebar.header("Filters")
text_columns = [name for name, dtype in df.schema.items() if dtype == pl.String]

if not text_columns:
    st.warning("No text columns found. Add filters manually based on your dataset schema.")
    st.dataframe(df.head(50))
    st.stop()

filter_col = st.sidebar.selectbox("Filter column", text_columns)
values = ["All"] + df.select(pl.col(filter_col).drop_nulls().unique().sort()).to_series().to_list()
selected_value = st.sidebar.selectbox("Value", values)

top_n = st.sidebar.slider("Top N", min_value=5, max_value=30, value=10)

filtered = filter_data(df, selected_value, filter_col)

metric_1, metric_2, metric_3 = st.columns(3)
metric_1.metric("Rows", f"{filtered.height:,}")
metric_2.metric("Columns", f"{filtered.width:,}")
metric_3.metric("Filter", selected_value)

st.subheader(f"Top {top_n} values by selected dimension")
category_col = st.selectbox("Chart dimension", text_columns, index=0)
chart_data = top_categories(filtered, category_col, top_n=top_n)

fig = px.bar(
    chart_data,
    x=category_col,
    y="n_rows",
    title=f"Top {top_n} values in {category_col}",
    labels={category_col: category_col.replace("_", " ").title(), "n_rows": "Rows"},
)
st.plotly_chart(fig, width="stretch")

st.subheader("Data preview")
st.dataframe(filtered.head(100), width="stretch")
