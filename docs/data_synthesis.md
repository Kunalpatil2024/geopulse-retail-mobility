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
about 390 m north. Each has a 250 m evaluation catchment. Exactly 25% of devices
in each chunk are assigned morning routes through A, with 30% of that cohort
also routing through B before A. The route pings are retained on weekdays so
the scenario can be measured in the generated point data. These are illustrative
synthetic planning coordinates, not surveyed store locations. Store metadata is
in [`store_locations.csv`](store_locations.csv); commercial zoning polygons are
in [`commercial_zones.geojson`](commercial_zones.geojson).

## Snowflake setup and load

1. Copy `.env.example` to `.env`, enter the Snowflake account credentials, and
   create/use the `GEOPULSE` database and a role with schema, table, and stage
   permissions.
2. Execute [`snowflake_setup.sql`](snowflake_setup.sql) in Snowflake. It creates
   raw ping, store, and commercial-zone tables with `GEOGRAPHY` columns and
   idempotently seeds the two sites and three zones.
3. Generate Parquet parts, then from SnowSQL upload them to the internal stage:

   ```sql
   PUT file://C:\absolute\path\to\geopulse-retail-mobility\data\pings\part-*.parquet
     @GEOPULSE.RAW.PING_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   ```

4. Run the `COPY INTO GEOPULSE.RAW.MOBILE_PINGS` statement at the end of the SQL
   file. It converts Parquet fields and creates each ping's geography point from
   longitude/latitude. Snowflake's load history prevents reloading the same
   staged files unless they are force-loaded; avoid force-loading to prevent
   duplicates.

The same SQL file defines each raw ping's scalar coordinates alongside its
`GEOGRAPHY` point, keeping the data straightforward to inspect and spatially
query.
