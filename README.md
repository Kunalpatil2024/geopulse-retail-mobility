# GeoPulse: Hyper-Local Retail Mobility Analytics

GeoPulse analyzes anonymized mobile GPS pings to show how foot traffic flows through a city across the day. Retailers can test a new store location and see how much traffic it would cannibalize from an existing store before opening. Pipeline: Snowflake -> Apache Sedona (PySpark) -> dbt -> Kepler.gl (React), orchestrated with Airflow.

## Team

| Member | Focus | Project areas |
|---|---|---|
| M1 | Data synthesis & Snowflake | `data_synthesis/`, `docs/` |
| M2 | Spatial processing (Sedona/PySpark) | `spark_jobs/` |
| M3 | dbt modeling | `dbt_project/` |
| M4 | Dashboard & Airflow | `dashboard/`, `airflow/` |

## Weekly progress

- [ ] Week 1
- [ ] Week 2
- [ ] Week 3
- [ ] Week 4
- [ ] Final review

## Setup

1. Clone the repository:
   ```sh
   git clone https://github.com/Kunalpatil2024/geopulse-retail-mobility.git
   cd geopulse-retail-mobility
   ```
2. Create and activate a virtual environment:
   ```sh
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your Snowflake credentials.

## Workflow

Use one branch per member and merge changes via Pull Request. Commit style: `feat:`, `fix:`, `docs:`, or `chore:`.

## M1: data synthesis and Snowflake

Generate the default Nashik mobility dataset with
`python data_synthesis\generate_pings.py`. The command writes chunked Parquet
files under `data\pings\` and refreshes the 1,000-row CSV example in `docs\`.
See [docs/SNOWFLAKE_SETUP.md](docs/SNOWFLAKE_SETUP.md) for Snowflake trial
setup, table creation, credentials, loading, and the pipeline audit.

### Load and verify

After configuring `.env` and generating the Parquet files, load the raw
Snowflake tables and run the audit:

```powershell
python data_synthesis\load_to_snowflake.py
python data_synthesis\pipeline_check.py
```

The loader prints row counts and elapsed time. The audit prints PASS/FAIL
checks and writes `docs/pipeline_audit.md`; see the setup guide for
`--truncate` and `--force` behavior.
