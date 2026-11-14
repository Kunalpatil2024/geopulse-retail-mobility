# Snowflake setup, loading, and audit

## 1. Create a Snowflake trial account

1. Sign up at [signup.snowflake.com](https://signup.snowflake.com/) and follow
   the email verification and account activation steps.
2. Select an available cloud provider and region, then open the new account in
   Snowsight. Trial options and available regions may vary.
3. Ensure the role you use can create or use the `GEOPULSE_WH` warehouse,
   `GEOPULSE` database, `RAW` and `ANALYTICS` schemas, and the team role. The
   setup SQL can be run with an administrative role if needed.

## 2. Find the account identifier

In Snowsight, open the account selector and choose **View account details**.
Copy the **Account identifier** into `SNOWFLAKE_ACCOUNT`. Prefer the current
organization-account format (for example, `myorg-account123`) rather than the
legacy account locator. Do not include the URL scheme or
`.snowflakecomputing.com`.

## 3. Create the database and raw tables

From the repository root, copy `.env.example` to `.env` and enter your account,
user, password, and role. The warehouse, database, and schema default to
`GEOPULSE_WH`, `GEOPULSE`, and `RAW`.

Open and run [`snowflake_setup.sql`](snowflake_setup.sql) with a role that can
create the warehouse, database, schemas, and `GEOPULSE_TEAM_ROLE`. It creates
the X-Small `GEOPULSE_WH` warehouse (60-second auto-suspend), the `GEOPULSE`
database, `RAW` and `ANALYTICS` schemas, `DEVICE_PINGS`, `STORES`, and `ZONES`,
the Parquet file format, and the internal `PING_STAGE`. It seeds all three
stores and the commercial zones and grants the team role the required access.
Have an administrator grant `GEOPULSE_TEAM_ROLE` to the Snowflake user that
will run the loader, then set `SNOWFLAKE_ROLE=GEOPULSE_TEAM_ROLE` in `.env`.

The loader uses these table names and columns from the setup file.
Parquet records contain `device_id`, `lat`, `long`, and `timestamp`; loaded
locations use `ST_MAKEPOINT(long, lat)`. Store and zone records are merged by
their IDs, and zone geometry is converted with `TO_GEOGRAPHY`.

## 4. Install dependencies and generate pings

Install the requirements and generate the default dataset:

```powershell
pip install -r requirements.txt
python data_synthesis\generate_pings.py
```

The generator writes numbered Parquet parts to `data\pings\`. Keep those local
files until the audit completes; the audit compares their row count with
Snowflake.

## 5. Load the data

Run the loader from the repository root:

```powershell
python data_synthesis\load_to_snowflake.py
```

It reads credentials from `.env`, uploads the Parquet parts to the internal
stage with parallel `PUT`, copies them into `GEOPULSE.RAW.DEVICE_PINGS`, and
merges `docs\store_locations.csv` and `docs\commercial_zones.geojson` into
their raw tables. Normal reruns do not reload previously copied Parquet files;
store and zone merges update matching IDs instead of duplicating them. The
loader prints the three row counts and total elapsed load time.

Options:

- `--truncate` truncates all three raw tables before loading. This is
  destructive to their current rows; use it only when you intend a clean
  reload. It also forces the Parquet copy so the just-truncated table is
  populated again.
- `--force` overwrites same-named stage files and forces the Parquet copy.
  Unless the tables were truncated, this can duplicate ping rows.
- `--ping-dir PATH` selects a different directory of numbered Parquet files.

## 6. Run the pipeline audit

After loading, run:

```powershell
python data_synthesis\pipeline_check.py
```

The audit prints PASS/FAIL for the local-versus-Snowflake ping count, NULL
locations, morning/evening hourly traffic versus night traffic, the city
bounding box (latitude 19.85–20.15, longitude 73.60–74.00), and pings within
500 m of both stores. It writes the results to
[`pipeline_audit.md`](pipeline_audit.md) and exits with status 1 if any check
fails. Keep the same local Parquet files that were loaded for the row-count
comparison.
