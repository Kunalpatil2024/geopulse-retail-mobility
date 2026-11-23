# GeoPulse – Retail Mobility Analytics

GeoPulse is a geospatial analytics project that uses synthetic GPS data to understand customer movement, store footfall, and retail location performance.

The goal is to help retailers identify high-traffic areas and understand potential customer cannibalization between nearby stores.

## Project Objectives

- Generate synthetic GPS movement data.
- Store location data in Snowflake.
- Perform spatial analysis using Apache Sedona.
- Calculate hourly store footfall using dbt.
- Visualize customer movement using Kepler.gl.
- Automate workflows using Apache Airflow.
- Validate synthetic GPS records before loading them into the analytics pipeline.

## Tech Stack

- Python, Pandas, NumPy
- Snowflake SQL
- Apache Spark and Sedona
- dbt
- Kepler.gl and React
- Apache Airflow
- Git and GitHub

## Project Structure

```text
geopulse-retail-mobility/
├── data_synthesis/
├── spark_jobs/
├── dbt_project/
├── dashboard/
├── airflow/
├── docs/
├── tests/
├── requirements.txt
└── README.md
```

## Data Quality & Validation

The planned GPS validation module, `data_synthesis/validate_pings.py`, checks
for missing values, duplicate GPS records, invalid latitude and longitude, and
invalid timestamps. The module is not present in the repository yet, so these
checks are not currently implemented.

Once the module is added, run it from the project root:

```bash
python data_synthesis/validate_pings.py
```

The expected generated report is `docs/data_quality_report.json`; it is not
present until the validator is implemented and run.

## Current Progress

- [x] Project structure created
- [x] Synthetic GPS data generator
- [x] Store locations and sample dataset
- [x] Snowflake setup SQL
- [x] Snowflake loader
- [x] Data contract and documentation
- [ ] GPS data quality validation (`data_synthesis/validate_pings.py` and report pending)
- [ ] Complete Snowflake pipeline validation
- [ ] Spatial joins using Sedona
- [ ] dbt analytics models
- [ ] Interactive dashboard
- [ ] Airflow automation

## Team Branches

| Member | Responsibility | Branch |
|---|---|---|
| M1 | Data & Snowflake | m1-data-snowflake |
| M2 | Spatial Processing | m2-sedona-spatial |
| M3 | dbt Modeling | m3-dbt-models |
| M4 | Dashboard & Airflow | m4-dashboard-airflow |

## Project status (23 Nov 2026)

### Deliverables by member

| Member | Deliverable | Location | Status |
|---|---|---|---|
| M1 | Mock GPS ping generator | `data_synthesis/generate_pings.py` | Done |
| M1 | Store locations (Store A, Store B) | `docs/store_locations.csv` | Done |
| M1 | Commercial zoning polygons | `docs/commercial_zones.geojson` | Done |
| M1 | 1,000-row sample for teammates | `docs/sample_pings_1000.csv` | Done |
| M1 | Snowflake setup SQL (`GEOGRAPHY` tables) | `docs/snowflake_setup.sql` | Done |
| M1 | Generator tests | `tests/test_generate_pings.py` | Done |
| M1 | Data contract and contribution workflow | `docs/` | Done |
| M1 | Snowflake load and pipeline audit | `data_synthesis/` | In progress |
| M2 | Sedona catchment spatial joins | `spark_jobs/` | In progress |
| M3 | dbt models and cannibalization SQL | `dbt_project/` | In progress |
| M4 | Kepler.gl dashboard and Airflow DAG | `dashboard/`, `airflow/` | In progress |

### What M1 finished

- Set up the repository, folder structure, `.gitignore`, and
  `.env.example` credentials template.
- Built a Python generator that simulates commuters with home and work locations.
- Modeled morning (8-9 am) and evening (5-6 pm) rush hours plus GPS noise.
- Saved the pings as Parquet files so millions of rows stay small and fast to load.
- Defined Store A (existing) and Store B (proposed) so cannibalization can be measured.
- Added commercial zoning polygons as GeoJSON for the spatial join.
- Wrote the Snowflake setup SQL with `GEOGRAPHY` columns.
- Documented the data contract so M2, M3, and M4 know the schemas.
- Added pytest tests and the team contribution workflow.
- Wrote the full project README.

### Next steps

1. Create the Snowflake database and tables from `docs/snowflake_setup.sql`.
2. Load the full dataset into `RAW.DEVICE_PINGS`.
3. Run the pipeline audit (row counts, null locations, rush-hour peaks).
4. Share Snowflake access with M2, M3, and M4 privately, never in the repository.
5. Support the team during the Weeks 3-4 integration.

### Notes

- The ping data is synthetic by design, which protects privacy and keeps the
  scenario controlled.
- Store B is placed so that a known share of Store A's morning commuters also
  pass it.
- `main` requires a Pull Request, so all changes go through a branch and review.
- Never commit `.env`, credentials, or large data files.

### How to verify the project

Run these commands from the repository root:

```powershell
pytest
```

Generate the default synthetic dataset:

```powershell
python data_synthesis\generate_pings.py
```

Load the generated Parquet parts and reference data into Snowflake:

```powershell
python data_synthesis\load_to_snowflake.py
```

Run the Snowflake-versus-local pipeline audit:

```powershell
python data_synthesis\pipeline_check.py
```

The loader and audit require the Snowflake environment variables documented in
`docs/SNOWFLAKE_SETUP.md`. The generator creates numbered Parquet parts in
`data\pings\`; those generated files are intentionally ignored by Git. The
audit compares that local input with `GEOPULSE.RAW.DEVICE_PINGS` and writes
`docs/pipeline_audit.md` when it runs.

## Objective

Build an end-to-end retail mobility analytics pipeline that transforms location data into actionable business insights.

## License

MIT