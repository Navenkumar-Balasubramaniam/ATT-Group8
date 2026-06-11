# ATT-Group8

This repository contains the working notebook and dashboard for the ATT Plane group project, plus a few optional troubleshooting files for setup issues.

## Project Overview

This is a take-home airline analytics project built around the ATTPLANE DB2 database. The goal is to prepare data with Polars, then present useful airline business insights in a Streamlit dashboard.

The project should answer real operational questions such as:

- Which routes, cabins, or departure periods generate the most value?
- How is the fleet being used, and where are the capacity or maintenance risks?
- What patterns appear in passenger, route, or ticket performance over time?

The intended stack is:

- Polars for loading, cleaning, joining, and aggregating data
- Streamlit for the dashboard UI
- Plotly for visualizations
- SQLAlchemy and the IBM DB2 driver for database access

The main deliverables are a working notebook, prepared data files or transformations, and a Streamlit app that explains the assumptions and findings clearly.

## Team Scaffold

The repository is organized so five people can work in parallel without overlapping ownership:

1. DB2 connection and ingestion.
2. Cleaning, joins, and feature engineering.
3. Revenue and route analysis.
4. Fleet or passenger analysis.
5. Streamlit app and presentation.

The detailed handoff plan lives in [docs/team_workplan.md](docs/team_workplan.md), and the folder layout is summarized in [docs/repo_scaffold.md](docs/repo_scaffold.md).

## Start Here

1. Open [G8_Project.ipynb](G8_Project.ipynb) to run the DB2 connection test, inspect tables, and prepare data.
2. Run [app.py](app.py) with Streamlit once the prepared Parquet file exists.
3. Use [plane_db_take_home_assignment.md](plane_db_take_home_assignment.md) as the project brief and requirements reference.

## How to Run

1. Activate the project environment.
2. Open [G8_Project.ipynb](G8_Project.ipynb) and run the notebook cells in order.
3. If the notebook creates `data/main_clean.parquet`, launch the dashboard with Streamlit.

Example commands:

```bash
uv sync
uv run streamlit run app.py
```

## Repository Layout

```text
ATT-Group8/
├── G8_Project.ipynb               # Main notebook for connection, exploration, and data prep
├── app.py                          # Streamlit dashboard
├── src/                            # Reusable DB, analysis, and visualization helpers
├── docs/                           # Team plan and scaffold notes
├── data/raw/                       # Source extracts or snapshots
├── data/processed/                 # Cleaned intermediate datasets
├── data/output/                    # Final dashboard-ready datasets
├── plane_db_take_home_assignment.md # Project brief and requirements
├── Exploratory.ipynb               # Optional scratch notebook
├── fix_db_setup.py                 # Optional DB2 connection helper
├── fix.md                          # Optional troubleshooting notes
└── README.md                       # Project overview and setup notes
```

## Main Files

- [G8_Project.ipynb](G8_Project.ipynb): primary exploratory notebook and preparation workflow.
- [app.py](app.py): Streamlit dashboard template.
- [plane_db_take_home_assignment.md](plane_db_take_home_assignment.md): assignment brief and deliverable expectations.

## Optional Support Files

- [Exploratory.ipynb](Exploratory.ipynb): scratch notebook for experiments and ad hoc analysis.
- [fix_db_setup.py](fix_db_setup.py): local DB2 driver patch and connection helper for the `ibm_db` schema issue.
- [fix.md](fix.md): written troubleshooting guide for the same DB2 connection problem.
- [docs/team_workplan.md](docs/team_workplan.md): recommended division of work for five colleagues.
- [docs/repo_scaffold.md](docs/repo_scaffold.md): high-level explanation of the folder structure.

## Notes

- Keep the support files if teammates may need to reproduce the DB2 fix.
- The main project should still live in the notebook, cleaned Parquet outputs, and the Streamlit app.