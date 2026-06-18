# Data Contract

This document is the single source of truth for the data the dashboard pipeline reads and
writes. It "staples" inputs to outputs so the prep script, the notebooks, and the Streamlit
app stay consistent. The machine-usable version of this contract lives in
[`src/contracts.py`](../src/contracts.py) — code should import paths and column lists from
there rather than hardcoding strings.

Pipeline: **raw → processed → output → app**

```
data/raw/*.parquet  ──clean──►  data/processed/*_clean.parquet
                                        │
                                  enrich + join
                                        ▼
                         data/processed/master_flight_dashboard.parquet
                                        │
                                   aggregate
                                        ▼
                            data/output/*.parquet  ──►  app.py
```

Build everything with one command (no database connection required):

```bash
uv run python scripts/build_dashboard_data.py
```

---

## Tier 1 — Inputs: `data/raw/<table>.parquet`

The six DB2 extracts (schema `ATTGRP8`). Row counts as observed:

| table | rows | notes |
|---|---|---|
| `airplanes` | 796 | fleet / aircraft master |
| `airports` | 30 | airport reference |
| `flights` | 1,758,638 | one row per flight occurrence (fact table) |
| `passengers` | 500,000 | passenger master (not used by the dashboard yet) |
| `routes` | 624 | route definitions |
| `tickets` | 248,622,081 | revenue fact — **3.4 GB; must be cleaned via streaming** |

### Raw schemas

**airplanes**: `aircraft_registration(str)`, `model(str)`, `seats_business(i64)`,
`seats_premium(i64)`, `seats_economy(i64)`, `crew_members(i64)`, `build_date(date)`,
`fuel_gallons_hour(i64)`, `maintenance_last_acheck(date)`, `maintenance_last_bcheck(date)`,
`maintenance_takeoffs(i64)`, `maintenance_flight_hours(i64)`, `total_flight_distance(i64)`

**airports**: `iata_code(str)`, `airport(str)`, `city(str)`, `country(str)`, `continent(str)`,
`timezone(str)`, `latitude(f64)`, `longitude(f64)`, `airport_tax(f64)`

**flights**: `flight_id(str)`, `flight_leg(i64)`, `frequency(str)`, `route_code(str)`,
`departure(datetime)`, `arrival(datetime)`, `airplane(str)`, `price_economy(f64)`,
`price_premium(f64)`, `price_business(f64)`

**passengers**: `id(i64)`, `firstnme(str)`, `midinit(str)`, `lastname(str)`, `gender(str)`,
`birth_date(date)`, `passport(str)`, `country(str)`, `vipcard(str)`, `phone(str)`, `email(str)`

**routes**: `route_code(str)`, `origin(str)`, `destination(str)`, `parent_route(str)`,
`leg_number(i64)`, `distance(i64)`, `flight_minutes(i64)`

**tickets**: `ticket_id(str)`, `passenger_id(i64)`, `flight_id(str)`, `route_code(str)`,
`departure(datetime)`, `class(str)`, `seat(str)`, `price(f64)`, `airport_tax(f64)`,
`local_tax(f64)`, `total_amount(f64)`

---

## Tier 2 — Processed: `data/processed/`

Cleaning rules (`src/data_clean.py`): trim text, turn `""`/`NA`/`N/A`/`NULL`/`NONE`/`NAN`
into nulls, parse the date columns listed in `contracts.DATE_COLUMNS_BY_TABLE` /
`DATETIME_COLUMNS_BY_TABLE`, drop exact duplicate rows.

| file | how it's built |
|---|---|
| `airplanes_clean.parquet` … `routes_clean.parquet` | eager clean of each small raw table |
| `master_flight_dashboard.parquet` | enrich + left-join `flights ← routes ← airplanes ← origin/destination airports` → **1,758,638 rows × 71 cols**, one row per flight |

> **tickets is not materialised.** The 248M-row file is never cleaned to disk: a global
> `.unique()` over it defeats streaming and exhausts memory (it OOM-kills the kernel). Instead
> the prep script cleans it *lazily* (`scan_clean_table`: trim + parse `departure`, **no dedup**)
> and aggregates it with the streaming engine (`collect(engine="streaming")`) straight into the
> small `revenue_*` outputs below. Group cardinality is tiny (≤624 routes, 12 months, a few
> classes), so peak memory stays low while the 3.4 GB file is read once, sequentially.

Master column prefixes (from `src/data_model._prefix_for_join`): route columns → `route_*`,
aircraft → `airplane_*`, origin airport → `origin_*`, destination airport → `destination_*`.
Derived flags: `is_domestic_route`, `is_same_continent_route`. Tickets and passengers are
**not** part of the master join (passengers connect to flights only through tickets), so
revenue is produced by separate tickets aggregations below.

---

## Tier 3 — Outputs: `data/output/` (consumed by `app.py`)

Small, dashboard-ready aggregates. `app.py` reads only these plus `master_flight_dashboard.parquet`.

| file | grain | columns |
|---|---|---|
| `flights_by_route.parquet` | route | `route_code`, `route_origin`, `route_destination`, `total_flights`, `avg_distance_km`, `avg_duration_min` |
| `flights_by_continent.parquet` | origin continent | `origin_continent`, `total_flights`, `total_distance_km` |
| `fleet_usage.parquet` | aircraft | `airplane`, `airplane_model`, `total_flights`, `total_distance_km` |
| `fleet_maintenance.parquet` | aircraft | `airplane`, `airplane_model`, `airplane_build_date`, `airplane_maintenance_flight_hours`, `airplane_total_flight_distance`, `aircraft_age_years` |
| `revenue_by_route.parquet` | route | `route_code`, `route_origin`, `route_destination`, `distance_band`, `n_tickets`, `total_revenue`, `avg_ticket_price` |
| `revenue_by_month.parquet` | year+month | `year`, `month`, `n_tickets`, `total_revenue` |
| `revenue_by_class.parquet` | cabin class | `class`, `n_tickets`, `total_revenue`, `avg_ticket_price` |

Column meanings: `total_flights` = count of flight rows; `avg_distance_km` / `avg_duration_min`
= mean of `route_distance` / `route_flight_minutes`; `total_distance_km` = summed route distance;
`total_revenue` = sum of ticket `total_amount` (price + airport tax + local tax);
`avg_ticket_price` = mean ticket `price`; `n_tickets` = ticket count;
`aircraft_age_years` = `2026 − build_year`.

The required-columns lists are enforced at build time by `contracts.validate_output(df, name)`.
