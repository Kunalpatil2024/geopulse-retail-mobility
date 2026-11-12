-- Run in the GEOPULSE database with a role that can create schemas and stages.
CREATE SCHEMA IF NOT EXISTS GEOPULSE.RAW;

CREATE OR REPLACE FILE FORMAT GEOPULSE.RAW.PING_PARQUET
  TYPE = PARQUET;

CREATE STAGE IF NOT EXISTS GEOPULSE.RAW.PING_STAGE
  FILE_FORMAT = GEOPULSE.RAW.PING_PARQUET;

CREATE TABLE IF NOT EXISTS GEOPULSE.RAW.MOBILE_PINGS (
  device_id STRING NOT NULL,
  lat FLOAT NOT NULL,
  long FLOAT NOT NULL,
  timestamp_utc TIMESTAMP_TZ NOT NULL,
  location GEOGRAPHY NOT NULL
);

CREATE TABLE IF NOT EXISTS GEOPULSE.RAW.STORES (
  store_id STRING NOT NULL,
  store_name STRING NOT NULL,
  status STRING NOT NULL,
  lat FLOAT NOT NULL,
  long FLOAT NOT NULL,
  catchment_radius_m FLOAT NOT NULL,
  location GEOGRAPHY NOT NULL
);

CREATE TABLE IF NOT EXISTS GEOPULSE.RAW.COMMERCIAL_ZONES (
  zone_id STRING NOT NULL,
  zone_name STRING NOT NULL,
  zone_type STRING NOT NULL,
  boundary GEOGRAPHY NOT NULL
);

-- Store B is a proposed site used to evaluate morning commuter interception.
MERGE INTO GEOPULSE.RAW.STORES AS target
USING (
  SELECT column1::STRING AS store_id, column2::STRING AS store_name,
         column3::STRING AS status, column4::FLOAT AS lat,
         column5::FLOAT AS long, column6::FLOAT AS catchment_radius_m
  FROM VALUES
    ('store_a', 'Store A', 'existing', 19.9975, 73.7898, 250),
    ('store_b', 'Store B', 'proposed', 20.0010, 73.7898, 250)
) AS source
ON target.store_id = source.store_id
WHEN MATCHED THEN UPDATE SET
  store_name = source.store_name, status = source.status,
  lat = source.lat, long = source.long,
  catchment_radius_m = source.catchment_radius_m,
  location = ST_MAKEPOINT(source.long, source.lat)
WHEN NOT MATCHED THEN INSERT (
  store_id, store_name, status, lat, long, catchment_radius_m, location
) VALUES (
  source.store_id, source.store_name, source.status, source.lat, source.long,
  source.catchment_radius_m, ST_MAKEPOINT(source.long, source.lat)
);

MERGE INTO GEOPULSE.RAW.COMMERCIAL_ZONES AS target
USING (
  SELECT column1::STRING AS zone_id, column2::STRING AS zone_name,
         column3::STRING AS zone_type, column4::STRING AS boundary_wkt
  FROM VALUES
    ('zone_cbd', 'Central Business District', 'commercial',
     'POLYGON((73.778 19.985,73.800 19.985,73.800 20.010,73.778 20.010,73.778 19.985))'),
    ('zone_east', 'East Commercial Corridor', 'commercial',
     'POLYGON((73.800 19.995,73.825 19.995,73.825 20.020,73.800 20.020,73.800 19.995))'),
    ('zone_west', 'West Retail Corridor', 'commercial',
     'POLYGON((73.760 19.985,73.778 19.985,73.778 20.005,73.760 20.005,73.760 19.985))')
) AS source
ON target.zone_id = source.zone_id
WHEN MATCHED THEN UPDATE SET
  zone_name = source.zone_name, zone_type = source.zone_type,
  boundary = TO_GEOGRAPHY(source.boundary_wkt)
WHEN NOT MATCHED THEN INSERT (zone_id, zone_name, zone_type, boundary)
VALUES (
  source.zone_id, source.zone_name, source.zone_type,
  TO_GEOGRAPHY(source.boundary_wkt)
);

-- Upload generated part-*.parquet files to @GEOPULSE.RAW.PING_STAGE first.
COPY INTO GEOPULSE.RAW.MOBILE_PINGS
  (device_id, lat, long, timestamp_utc, location)
FROM (
  SELECT
    $1:device_id::STRING,
    $1:lat::FLOAT,
    $1:long::FLOAT,
    $1:timestamp::TIMESTAMP_TZ,
    ST_MAKEPOINT($1:long::FLOAT, $1:lat::FLOAT)
  FROM @GEOPULSE.RAW.PING_STAGE
)
FILE_FORMAT = (FORMAT_NAME = GEOPULSE.RAW.PING_PARQUET)
PATTERN = '.*part-[0-9]{4}[.]parquet'
ON_ERROR = 'ABORT_STATEMENT';
