# ATT Group 8

This repository contains the ATTPLANE group project. The current focus is a
simple, beginner-friendly Polars data preparation workflow that starts with raw
Parquet files, inspects and cleans them, adds useful business features, and
builds one dashboard-ready master table.

The main working notebook is:

- [notebooks/Exploratory.ipynb](notebooks/Exploratory.ipynb)

The main dashboard-ready output is:

- `data/processed/master_flight_dashboard.parquet`

## Project Goal

The goal is to prepare airline data for analysis and a later Streamlit
dashboard. The cleaned and enriched data should support questions such as:

- Which routes are short, medium, long, or very long?
- Which flights happen by month, weekday, hour, or weekend?
- What airplane capacity is available by model and route?
- Which routes are domestic or same-continent routes?
- Which airport, route, and airplane fields can be used in dashboard filters?

## Current Pipeline

The data preparation workflow is split into small modules:

| Step | File | Purpose |
| --- | --- | --- |
| Data loading | `src/pull_data.py` | Pull raw DB2 tables into `data/raw/` as Parquet files. |
| Inspection | `src/data_inspect.py` | Display available tables, summary statistics, and missing/null counts. |
| Cleaning | `src/data_clean.py` | Trim strings, convert obvious missing values to null, parse selected dates, and drop exact duplicates. |
| Enrichment | `src/data_enrich.py` | Add business features to each individual table. |
| Modeling | `src/data_model.py` | Join the enriched tables and verify row counts/keys. |
| Notebook | `notebooks/Exploratory.ipynb` | Runs the full workflow in order and saves the master table. |

The code is intentionally written in straightforward Polars so it is easier to
read, explain, and adjust.

## Master Table

The final master table is saved as:

```text
data/processed/master_flight_dashboard.parquet
```

It currently joins:

- `flights`
- `routes`
- `airplanes`
- `airports` twice: once for the origin airport and once for the destination airport

It does not include `tickets` or ticket-based passenger joins yet. The current
`data/raw/tickets.parquet` file needs to be re-pulled because it is not a valid
Parquet file.

The master table keeps all columns from the joined/enriched tables. To avoid
ambiguous duplicate names:

- flight columns keep their original names
- route columns use `route_`
- airplane columns use `airplane_`
- origin airport columns use `origin_`
- destination airport columns use `destination_`

Example columns:

```text
flight_id
route_code
departure_date
route_distance_band
airplane_total_seats
origin_city
destination_city
is_domestic_route
is_same_continent_route
```

## How To Run

Install dependencies:

```bash
uv sync
```

Open and run the notebook:

```text
notebooks/Exploratory.ipynb
```

The notebook is organized as:

1. Imports and setup
2. Pull/load raw data
3. Inspect and clean raw data
4. Enrich tables and build the master dashboard table

After running the notebook, the key output should exist here:

```text
data/processed/master_flight_dashboard.parquet
```

To run the Streamlit app later:

```bash
uv run streamlit run app.py
```

## How To Test

Run the data preparation tests:

```bash
uv run pytest tests/test_data_clean.py tests/test_data_inspect.py tests/test_data_enrich.py tests/test_data_model.py
```

Run all non-integration tests:

```bash
uv run pytest
```

Live DB2 tests are marked as integration tests and should only be run when the
DB2 connection is available.

## Repository Layout

```text
ATT-Group8/
|-- app.py
|-- notebooks/
|   |-- Exploratory.ipynb
|   `-- G8_Project.ipynb
|-- src/
|   |-- pull_data.py
|   |-- db.py
|   |-- data_inspect.py
|   |-- data_clean.py
|   |-- data_enrich.py
|   |-- data_model.py
|   |-- analysis.py
|   `-- viz.py
|-- tests/
|   |-- test_pull_data.py
|   |-- test_data_inspect.py
|   |-- test_data_clean.py
|   |-- test_data_enrich.py
|   `-- test_data_model.py
|-- data/
|   |-- raw/
|   |-- processed/
|   `-- output/
|-- docs/
|-- plane_db_take_home_assignment.md
|-- pyproject.toml
|-- uv.lock
`-- README.md
```

## Current Data Notes

- Cleaned intermediate tables are saved in `data/processed/` as
  `*_clean.parquet`. They are useful checkpoints for debugging and rerunning
  later steps without cleaning again.
- The final dashboard table is also saved in `data/processed/` as
  `master_flight_dashboard.parquet`.
- `tickets.parquet` currently needs to be re-pulled before ticket revenue or
  passenger-to-flight analysis can be added.
- Passenger enrichment exists in `src/data_enrich.py`, but passengers are not
  joined into the master table yet because tickets are the bridge table.

## Next Steps

Good follow-up tasks are:

- Re-pull `tickets.parquet`.
- Add ticket revenue features after tickets are readable.
- Join passengers through tickets once the ticket table is available.
- Build dashboard pages from `master_flight_dashboard.parquet`.
