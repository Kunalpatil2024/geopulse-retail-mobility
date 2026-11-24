# Data synthesis and Snowflake loading

## Synthetic Nashik pings

Install `requirements.txt`, then run:

```powershell
python data_synthesis\generate_pings.py
```

The defaults generate 100,000 anonymized device IDs over seven days starting
2026-11-02. Use `--devices`, `--days`, `--start-date` (`YYYY-MM-DD`), `--out-dir`,
`--seed`, and `--chunk-devices` to adjust the run. Each device chunk becomes a
Parquet part in the output directory; rerunning removes the prior numbered
`part-####.parquet` files there. The generator also refreshes
[`sample_pings_1000.csv`](sample_pings_1000.csv), a sorted 1,000-row sample from
the first devices (small test runs may produce fewer rows).

The generated records contain `device_id`, `lat`, `long`, and a timezone-aware
UTC `timestamp`. Device locations include broader residential distributions,
commercially clustered workplaces, irregular daytime pings, overnight home
pings, reduced/flatter weekend traffic, leisure trips, and GPS noise.

Store A is the existing site at 19.9975, 73.7898; Store B is a proposed site
about 700 m north. Store C is a control site. Each has a 250 m evaluation
catchment. Exactly 25% of devices in each chunk are assigned morning routes
through A, with 30% of that cohort also routing through B before A. This is a
synthetic scenario assumption for possible cannibalization, not an observed or
measured business result. The route pings are retained on weekdays so the
scenario can be measured in the generated point data. These are illustrative
synthetic planning coordinates, not surveyed store locations. Store metadata is
in [`store_locations.csv`](store_locations.csv); commercial zoning polygons are
in [`commercial_zones.geojson`](commercial_zones.geojson).

## Snowflake setup and load

For trial signup, account identifiers, database/table setup, credential
configuration, and the repeatable loader/audit commands, follow the
[Snowflake setup guide](SNOWFLAKE_SETUP.md). Run
[`snowflake_setup.sql`](snowflake_setup.sql) before the loader; it defines the
`GEOPULSE.RAW.DEVICE_PINGS`, `STORES`, and `ZONES` tables used by the scripts
here.

## End-to-end data flow

The pipeline currently implements generation, Parquet output, Snowflake
loading, and a Snowflake-versus-local audit. Spatial processing, dbt models,
the dashboard, and Airflow orchestration are planned; their directories
currently contain placeholders rather than runnable jobs.

| Stage | Owner | Input | Output | Status |
|---|---|---|---|---|
| 1. Generate | M1 | Generator options and random seed | Synthetic pings with `device_id`, `lat`, `long`, and `timestamp` | Implemented |
| 2. Write Parquet | M1 | Generated pings | Compressed, numbered files in `data/pings/` (gitignored) | Implemented |
| 3. Load into Snowflake | M1 | Parquet files and reference data | `GEOPULSE.RAW.DEVICE_PINGS`, `STORES`, and `ZONES` | Implemented |
| 4. Spatial processing | M2 | Raw pings and store/zone geometries | Pings associated with store catchments | Planned |
| 5. dbt modeling | M3 | Spatially enriched data | Hourly visitor and multi-store visit analytics | Planned |
| 6. Dashboard | M4 | Modeled analytics | Interactive mobility map | Planned |
| 7. Orchestration | M4 | Pipeline jobs and schedule | Scheduled refresh of spatial and analytics stages | Planned |

### 1–2. Generate and write pings

Run `python data_synthesis\generate_pings.py` from the repository root. By
default, it generates 100,000 synthetic devices over seven days, writes one
Parquet part per 10,000-device chunk, and refreshes the small CSV sample in
`docs/`. The timestamp is timezone-aware UTC. The generator adds GPS noise and
models commute, daytime, overnight, and leisure locations. Its commute routes
and store visits are synthetic scenario assumptions, not observed customer
behavior.

### 3. Upload and load into Snowflake

The loader uploads the local Parquet parts to the `GEOPULSE.RAW.PING_STAGE`
internal stage, then copies them into `GEOPULSE.RAW.DEVICE_PINGS`. It also
merges the store and commercial-zone reference data into `STORES` and `ZONES`.
During the copy, the loader converts the Parquet timestamp to `TIMESTAMP_TZ`
and builds `location` as `GEOGRAPHY`:

```sql
ST_MAKEPOINT(long, lat)
```

Snowflake point construction takes longitude first. The exact setup, required
credentials, load options, and audit command are in the
[Snowflake setup guide](SNOWFLAKE_SETUP.md). Keep credentials in `.env`, never
in source control.

### 4–7. Planned downstream stages

The planned spatial job will use Apache Sedona to associate pings with store
catchments and zones. Store reference data currently specifies a 250 m
evaluation radius. The existing pipeline audit separately checks proximity
and synthetic route overlap at 500 m; that audit radius is not the store
catchment definition.

The planned dbt layer is expected to provide hourly unique visitors per store
and multi-store visit/cannibalization metrics, with tests for data integrity
and traffic patterns. The dashboard and orchestration are also planned, not
implemented: the current repository does not yet include a React/Kepler.gl
map, H3 animation, or an Airflow DAG.

### Troubleshooting notes

| Symptom | Check |
|---|---|
| Points appear in the wrong location | Verify coordinate order: use `ST_MAKEPOINT(long, lat)`. |
| Snowflake load is slow | Avoid excessive small Parquet parts; increase `--chunk-devices` if the machine has enough memory. |
| Spark runs out of memory | When the spatial job is implemented, process the input in partitions rather than all at once. |
| Dashboard map is empty | Once the dashboard exists, check its time filter against the UTC timestamp range. |
