# ATT Group 8

This repository contains the ATTPLANE group project: a Polars data preparation
workflow that starts from raw Parquet files, cleans and enriches them, builds one
dashboard-ready master table plus small aggregates, and serves them through a
Streamlit dashboard.

Quick start (after cloning): see **[How To Run (first time)](#how-to-run-first-time)** —
place the raw files, run `scripts/build_dashboard_data.py`, then
`uv run streamlit run app.py`.

Key entry points:

- Prep script: `scripts/build_dashboard_data.py` (raw -> processed -> output)
- Dashboard: `app.py`
- Notebooks: [notebooks/Exploratory.ipynb](notebooks/Exploratory.ipynb), `notebooks/Analysis.ipynb`
- Data contract (source of truth): `src/contracts.py` + [docs/data_contract.md](docs/data_contract.md)

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

It does not include `tickets` or ticket-based passenger joins (tickets are the
bridge table). Revenue is instead produced as separate aggregates streamed
directly from `data/raw/tickets.parquet` into `data/output/revenue_*.parquet`.

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

## How To Run (first time)

### 0. Install dependencies

```bash
uv sync
```

### 1. Get the raw data into `data/raw/`

The repo ships the **folder skeleton only** — the actual Parquet files are
git-ignored (the raw `tickets.parquet` alone is ~3.4 GB). After cloning you must
populate `data/raw/` yourself with the six source tables:

```text
data/raw/airplanes.parquet
data/raw/airports.parquet
data/raw/flights.parquet
data/raw/passengers.parquet
data/raw/routes.parquet
data/raw/tickets.parquet
```

Two ways to obtain them:

- **Pull from DB2** (needs the course connection): run `src/pull_data.py`, which
  writes every table to `data/raw/` as Parquet.
- **Download / copy** the extracts from your team's shared storage and drop them
  into `data/raw/` with the exact names above.

### 2. Build all dashboard data (one command, no database needed)

```bash
uv run python scripts/build_dashboard_data.py
```

This cleans the small tables, builds `data/processed/master_flight_dashboard.parquet`,
and writes the seven small aggregates into `data/output/`. Tickets (248M rows) is
streamed, never loaded into memory, so it will not crash the kernel.

> Prefer the notebook? Open **[notebooks/Exploratory.ipynb](notebooks/Exploratory.ipynb)**
> and run every cell top-to-bottom (Imports → Pull/load raw → Inspect & clean →
> Enrich & build master). The tickets cleaning step (`clean_raw_tables`, cell with
> `1e106816`) now streams the big file. The prep script is the faster, headless path.

After step 2 you should have:

```text
data/processed/master_flight_dashboard.parquet
data/output/*.parquet   (7 files)
```

### 3. Run the Streamlit dashboard

```bash
uv run streamlit run app.py
```

It opens at `http://localhost:8501`. The app reads only the small prepared files —
it never touches DB2 or the raw tickets table. If the prepared data is missing it
shows an error telling you to run step 2 first.

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
|-- app.py                         # Streamlit dashboard (reads data/output + master)
|-- scripts/
|   `-- build_dashboard_data.py    # one-time prep: raw -> processed -> output
|-- notebooks/
|   |-- Exploratory.ipynb          # full cleaning/enrich/master workflow
|   |-- Analysis.ipynb             # route/fleet/revenue analyses
|   `-- G8_Project.ipynb
|-- src/                           # the group8 package (group8-attplane)
|   |-- config.py                  # CENTRAL CONFIG: all hardcoded values (paths, DB, thresholds)
|   |-- contracts.py               # DATA CONTRACT: paths + expected columns (source of truth)
|   |-- pull_data.py               # pull raw DB2 tables -> data/raw/
|   |-- db.py
|   |-- data_inspect.py
|   |-- data_clean.py              # cleaning (+ streaming path for tickets)
|   |-- data_enrich.py
|   |-- data_model.py              # join enriched tables -> master
|   |-- analysis.py                # flight/fleet/revenue aggregations
|   `-- viz.py
|-- tests/
|   |-- test_pull_data.py
|   |-- test_data_inspect.py
|   |-- test_data_clean.py
|   |-- test_data_enrich.py
|   `-- test_data_model.py
|-- data/                          # folder skeleton tracked; .parquet/.csv git-ignored
|   |-- raw/        <- INPUTS you provide (the 6 DB2 extracts)
|   |-- processed/  <- generated: *_clean.parquet + master_flight_dashboard.parquet
|   `-- output/     <- generated: 7 small dashboard-ready aggregates
|-- docs/
|   |-- data_contract.md           # human-readable input<->output contract
|   `-- ...
|-- plane_db_take_home_assignment.md
|-- pyproject.toml
|-- uv.lock
`-- README.md
```

> **`data/` is git-ignored except the folder skeleton.** Each subfolder keeps a
> `.gitkeep` so anyone cloning sees the expected layout, but the heavy `.parquet`
> files are never committed — you must place the raw files yourself (step 1 above).
> `processed/` and `output/` are produced by the prep script, not committed.

## Current Data Notes

- Cleaned intermediate tables are saved in `data/processed/` as
  `*_clean.parquet`. They are useful checkpoints for debugging and rerunning
  later steps without cleaning again.
- The final dashboard table is saved in `data/processed/` as
  `master_flight_dashboard.parquet`; the small dashboard aggregates are in
  `data/output/`.
- `tickets.parquet` (~248M rows) is never materialised as a cleaned file. It is
  streamed and aggregated straight into the `revenue_*` outputs, so it does not
  exhaust memory.
- Passenger enrichment exists in `src/data_enrich.py`, but passengers are not
  joined into the master table (tickets are the bridge table).

## Next Steps

Good follow-up tasks are:

- Join passengers through tickets for passenger-level analysis.
- Add more dashboard sections from `master_flight_dashboard.parquet`.
- Minor design polish on the Streamlit app.
