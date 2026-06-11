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
2. Move reusable cleaning logic into `src/analysis.py`.
3. Keep DB connection code in `src/db.py`.
4. Use `src/viz.py` for reusable chart functions.
5. Reserve `app.py` for the dashboard experience.
