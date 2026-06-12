# Team Workplan

This project is organized so 5 colleagues can work in parallel with clear ownership.

## Shared Goal

Build a Streamlit dashboard for the ATTPLANE DB2 data, using Polars for transformation and analysis.

## Next Week Focus

The dashboard should ship as a working MVP next week. Focus on one coherent story, not many partial ones.

Priority order:

1. Get the DB2 connection working reliably and save one clean dataset.
2. Build 3 core metrics that answer one business question.
3. Add 2 filters that actually change the view.
4. Add 3 charts or visual summaries that tell the same story.
5. Make the Streamlit app run end to end from prepared data.

Recommended dashboard direction:

- Revenue and route performance, if the ticket and route tables are usable.
- Fleet utilization, if aircraft and flight tables are cleaner.
- Passenger segmentation only if the joins are straightforward.

For next week, pick one primary story and one supporting story. Do not try to build all examples at once.

## Recommended Workstreams

### 1. Database and Ingestion
Owner: one person

Responsibilities:

- Confirm DB2 connectivity.
- Keep the reusable connection code in `src/db.py`.
- Read the required tables and save raw or staged extracts.
- Document any schema or driver issues.

Deliverables:

- Reliable DB2 connection helper.
- A repeatable table-loading workflow.
- Short notes on credentials, schema names, and known pitfalls.
- One prepared raw or staged extract for the rest of the team.

### 2. Data Cleaning and Modeling
Owner: one person

Responsibilities:

- Standardize column names and data types.
- Join the tables needed for the dashboard.
- Create reusable cleaning functions in `src/data_clean.py`.
- Create reusable feature engineering and joined modeling functions in `src/data_enrich.py`.
- Produce cleaned Parquet outputs in `data/processed/` or `data/output/`.

Deliverables:

- Cleaned dataset.
- Transformation functions.
- A short description of the chosen joins and assumptions.
- One dashboard-ready Parquet file.

### 3. Revenue and Route Analysis
Owner: one person

Responsibilities:

- Build route, cabin, and departure-period metrics.
- Identify the most valuable routes or schedules.
- Prepare one or more charts for management insight.

Deliverables:

- Revenue or route summary tables.
- At least one chart-ready dataset.
- A written insight summary.
- One metric that can be shown in the dashboard hero section.

### 4. Fleet or Passenger Analysis
Owner: one person

Responsibilities:

- Build a second business lens, such as fleet utilization or passenger segmentation.
- Add the needed metrics and filters.
- Document the business interpretation.

Deliverables:

- Fleet or passenger summary tables.
- Supporting visuals.
- A written insight summary.
- One chart or table that can act as the secondary dashboard view.

### 5. Streamlit App and Presentation
Owner: one person

Responsibilities:

- Keep `app.py` organized and runnable.
- Wire in filters, charts, and key metrics.
- Make sure the dashboard tells a coherent story.
- Prepare the presentation or demo narrative.

Deliverables:

- Working Streamlit app.
- Clear UI structure.
- Final slide or demo outline.
- A demo path that a teammate can click through in under two minutes.

## Suggested Handoff Order

1. Database work confirms the data is accessible.
2. Cleaning/modeling produces shared datasets.
3. Analysis owners build their metric tables.
4. App work wires the outputs into the dashboard.
5. One final pass checks the README, setup instructions, and demo flow.

## What To Avoid

- Do not build extra notebooks or side analyses that do not feed the dashboard.
- Do not optimize for a perfect model before the app works.
- Do not split into too many tiny charts that tell different stories.
- Do not leave the app depending on ad hoc manual notebook state.

## Team Milestone For Next Week

By next week, the team should be able to show:

- A working DB2-to-Parquet pipeline.
- A single Streamlit dashboard with one clear business narrative.
- At least 2 filters, 3 metrics, and 3 charts.
- A short explanation of the data choices and assumptions.

## File Ownership Guide

- `src/db.py`: ingestion and connection logic
- `src/data_clean.py`: raw table cleaning and type standardization
- `src/data_enrich.py`: feature engineering and joined modeling datasets
- `src/analysis.py`: analytical summaries and metrics
- `src/viz.py`: chart helpers
- `app.py`: Streamlit interface
- `G8_Project.ipynb`: exploratory analysis and validation
- `docs/team_workplan.md`: team coordination and task ownership
