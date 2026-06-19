# Project Scaffold

## Current Structure

- `G8_Project.ipynb`: main notebook for exploration and preparation
- `app.py`: Streamlit dashboard
- `src/`: reusable helper modules
- `docs/`: project coordination and notes
- `data/raw/`: source extracts or snapshots
- `data/processed/`: cleaned intermediate datasets
- `data/output/`: final dashboard-ready datasets

## Purpose

This layout keeps database access, transformation logic, and presentation logic separate so different people can work at the same time without stepping on each other.

## Team Workflow

1. Pull raw data into `data/raw/` or directly into notebook cells.
2. Keep reusable cleaning logic in `src/data_clean.py`.
3. Keep feature engineering and joined modeling datasets in `src/data_enrich.py`.
4. Keep DB connection code in `src/db.py`.
5. Use `src/analysis.py` for analytical summaries and metric tables.
6. Use `src/viz.py` for reusable chart functions.
7. Reserve `app.py` for the dashboard experience.
