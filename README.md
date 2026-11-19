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

## Project status

This status records the repository deliverables that are present today. A
status of **Done** means the corresponding tracked file or documentation is
present. **In progress** identifies work that has an executable implementation
but still needs an environment or handoff check. **Pending** identifies a
team area whose repository location currently contains only its placeholder.

### Deliverables by member

| Member | Deliverable path | Status |
|---|---|---|
| M1 | `data_synthesis/generate_pings.py` | Done |
| M1 | `data_synthesis/load_to_snowflake.py` | In progress |
| M1 | `data_synthesis/pipeline_check.py` | In progress |
| M1 | `docs/store_locations.csv` | Done |
| M1 | `docs/commercial_zones.geojson` | Done |
| M1 | `docs/sample_pings_1000.csv` | Done |
| M1 | `docs/snowflake_setup.sql` | Done |
| M1 | `docs/DATA_CONTRACT.md` | Done |
| M1 | `docs/data_synthesis.md` | Done |
| M1 | `docs/SNOWFLAKE_SETUP.md` | Done |
| M1 | `tests/test_generate_pings.py` | Done |
| M1 | `tests/test_snowflake_pipeline.py` | Done |
| M1 | `CONTRIBUTING.md` | Done |
| M1 | `README.md` | Done |
| M2 | `spark_jobs/.gitkeep` | Pending |
| M3 | `dbt_project/models/staging/.gitkeep` | Pending |
| M3 | `dbt_project/models/marts/.gitkeep` | Pending |
| M4 | `dashboard/.gitkeep` | Pending |
| M4 | `airflow/dags/.gitkeep` | Pending |

### What M1 finished

- Added the deterministic synthetic ping generator in
  `data_synthesis/generate_pings.py`.
- Added chunked Parquet output under the generator's `data/pings` directory.
- Added the sorted sample-data refresh for
  `docs/sample_pings_1000.csv`.
- Added the store reference file at `docs/store_locations.csv`.
- Added the commercial zone reference file at
  `docs/commercial_zones.geojson`.
- Added the Snowflake warehouse, database, schemas, role, file format, and
  stage definitions in `docs/snowflake_setup.sql`.
- Added the `GEOPULSE.RAW.DEVICE_PINGS` table definition.
- Added the `GEOPULSE.RAW.STORES` table definition.
- Added the `GEOPULSE.RAW.ZONES` table definition.
- Added the Snowflake loader in `data_synthesis/load_to_snowflake.py`.
- Added Parquet discovery and ordered stage upload handling to the loader.
- Added store and zone merge handling to the loader.
- Added the pipeline audit in `data_synthesis/pipeline_check.py`.
- Added checks for row-count parity and NULL locations to the audit.
- Added hourly traffic, city bounds, and store proximity checks to the audit.
- Added the morning Store A and Store B overlap check to the audit.
- Documented the source and loaded schemas in `docs/DATA_CONTRACT.md`.
- Documented generator behavior in `docs/data_synthesis.md`.
- Documented Snowflake setup, loading, and audit workflow in
  `docs/SNOWFLAKE_SETUP.md`.
- Added generator tests in `tests/test_generate_pings.py`.
- Added loader, setup SQL, reference-data, and audit tests in
  `tests/test_snowflake_pipeline.py`.
- Documented the branch and contribution workflow in `CONTRIBUTING.md`.
- Updated this README with the current project status and verification steps.

### Next steps

- Run `docs/snowflake_setup.sql` in the target Snowflake account.
- Configure the required Snowflake values from `.env.example` in a local
  ignored `.env` file.
- Generate the local Parquet parts before attempting a Snowflake load.
- Load the generated parts and reference files with the Snowflake loader.
- Run the pipeline audit against the same local Parquet directory.
- Audit the complete Snowflake pipeline and retain the generated audit report.
- Hand off the raw tables and data contract to M2 for Sedona processing.
- Hand off the raw tables and agreed contract to M3 for dbt models.
- Hand off the downstream contract and modeled outputs to M4 for dashboard and
  Airflow work.

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