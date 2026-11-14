# GeoPulse data contract

## Local input and generated pings

The generator writes `data/pings/part-####.parquet` files. Each Parquet row
contains:

| Column | Type | Meaning and units |
|---|---|---|
| `device_id` | string | Stable synthetic device identifier; not a real person or device. |
| `lat` | floating point | WGS84 latitude in decimal degrees. |
| `long` | floating point | WGS84 longitude in decimal degrees. |
| `timestamp` | timestamp with timezone | UTC instant; Parquet values are timezone-aware. |

`docs/sample_pings_1000.csv` is a small, sorted example with the same four
columns. Coordinate distances are in meters only when computed geospatially;
latitude/longitude values themselves are degrees. Longitude is the first
argument when constructing a point, e.g. `ST_MAKEPOINT(long, lat)`.

The generator's illustrative cannibalization scenario assigns 25% of devices
to a weekday morning route through Store A; about 30% of that cohort also passes
Store B before A. That is a synthetic routing assumption, not a measured
commercial outcome.

## Store and zone reference data

`docs/store_locations.csv` has `store_id`, `store_name`, `status`, `lat`,
`long`, and `catchment_radius_m`. Coordinates are WGS84 decimal degrees and
catchment radii are meters. Store A is existing, Store B is proposed about
700 m away, and Store C is the control.

`docs/commercial_zones.geojson` is a GeoJSON FeatureCollection. Its polygon
coordinates follow GeoJSON order `[longitude, latitude]` in WGS84 decimal
degrees. Feature properties provide `zone_id`, `zone_name`, and `zone_type`.

## Snowflake contract

Run `docs/snowflake_setup.sql` to create the `GEOPULSE` database, `RAW` and
`ANALYTICS` schemas, and the Snowflake objects below. The loader's defaults are
`GEOPULSE.RAW`; it uploads the local Parquet parts to `PING_STAGE` and loads:

| Table | Columns |
|---|---|
| `GEOPULSE.RAW.DEVICE_PINGS` | `device_id`, `lat`, `long`, `timestamp_utc`, `location` (`GEOGRAPHY`) |
| `GEOPULSE.RAW.STORES` | `store_id`, `store_name`, `status`, `lat`, `long`, `catchment_radius_m`, `location` (`GEOGRAPHY`) |
| `GEOPULSE.RAW.ZONES` | `zone_id`, `zone_name`, `zone_type`, `boundary` (`GEOGRAPHY`) |

`timestamp_utc` is timezone-aware UTC. `location` and `boundary` use Snowflake
`GEOGRAPHY`; point construction takes longitude before latitude. The file
format and internal stage are `GEOPULSE.RAW.PING_PARQUET` and
`GEOPULSE.RAW.PING_STAGE`.

## Handoff across the team

- **M1 — Data synthesis and Snowflake:** generate the Parquet files and load
  them with `data_synthesis/load_to_snowflake.py`.
- **M2 — Sedona/PySpark:** read `GEOPULSE.RAW.DEVICE_PINGS` for spatial
  processing, using `location` for geospatial operations and the separate
  latitude/longitude columns when numeric coordinates are needed. Read
  `STORES` and `ZONES` as reference layers.
- **M3 — dbt:** build models from the `RAW` tables and expose modeled,
  documented outputs in the `ANALYTICS` schema.
- **M4 — Kepler.gl/Airflow:** have orchestration consume the agreed M3
  `ANALYTICS` outputs; use the spatially enriched geometry and timestamp
  fields for dashboard layers and time controls.

The Snowflake trial, setup, load, and audit procedure is in
[`SNOWFLAKE_SETUP.md`](SNOWFLAKE_SETUP.md).
