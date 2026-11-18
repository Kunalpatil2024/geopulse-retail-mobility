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

## Objective

Build an end-to-end retail mobility analytics pipeline that transforms location data into actionable business insights.

## License

MIT