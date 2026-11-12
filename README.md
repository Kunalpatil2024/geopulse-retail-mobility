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
Snowflake table setup, store/zoning seed data, and the staged Parquet load steps
are documented in [docs/data_synthesis.md](docs/data_synthesis.md).
