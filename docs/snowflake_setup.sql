-- Run with a role that can create warehouses, databases, schemas, and roles.
CREATE WAREHOUSE IF NOT EXISTS GEOPULSE_WH
  WITH WAREHOUSE_SIZE = 'X-SMALL'
       AUTO_SUSPEND = 60
       AUTO_RESUME = TRUE
       INITIALLY_SUSPENDED = TRUE;

CREATE DATABASE IF NOT EXISTS GEOPULSE;
CREATE SCHEMA IF NOT EXISTS GEOPULSE.RAW;
CREATE SCHEMA IF NOT EXISTS GEOPULSE.ANALYTICS;
CREATE ROLE IF NOT EXISTS GEOPULSE_TEAM_ROLE;

CREATE OR REPLACE FILE FORMAT GEOPULSE.RAW.PING_PARQUET
  TYPE = PARQUET;

CREATE STAGE IF NOT EXISTS GEOPULSE.RAW.PING_STAGE
  FILE_FORMAT = GEOPULSE.RAW.PING_PARQUET;

CREATE TABLE IF NOT EXISTS GEOPULSE.RAW.DEVICE_PINGS (
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

CREATE TABLE IF NOT EXISTS GEOPULSE.RAW.ZONES (
  zone_id STRING NOT NULL,
  zone_name STRING NOT NULL,
  zone_type STRING NOT NULL,
  boundary GEOGRAPHY NOT NULL
);

-- Store B is the proposed site; Store C is the control site.
MERGE INTO GEOPULSE.RAW.STORES AS target
USING (
  SELECT column1::STRING AS store_id, column2::STRING AS store_name,
         column3::STRING AS status, column4::FLOAT AS lat,
         column5::FLOAT AS long, column6::FLOAT AS catchment_radius_m
  FROM VALUES
    ('store_a', 'Store A', 'existing', 19.9975, 73.7898, 250),
    ('store_b', 'Store B', 'proposed', 20.0038, 73.7898, 250),
    ('store_c', 'Store C', 'control', 19.9850, 73.7800, 250)
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

MERGE INTO GEOPULSE.RAW.ZONES AS target
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

GRANT USAGE ON WAREHOUSE GEOPULSE_WH TO ROLE GEOPULSE_TEAM_ROLE;
GRANT USAGE ON DATABASE GEOPULSE TO ROLE GEOPULSE_TEAM_ROLE;
GRANT USAGE ON SCHEMA GEOPULSE.RAW TO ROLE GEOPULSE_TEAM_ROLE;
GRANT USAGE ON SCHEMA GEOPULSE.ANALYTICS TO ROLE GEOPULSE_TEAM_ROLE;
GRANT CREATE TABLE ON SCHEMA GEOPULSE.ANALYTICS TO ROLE GEOPULSE_TEAM_ROLE;
GRANT CREATE TABLE, CREATE STAGE, CREATE FILE FORMAT
  ON SCHEMA GEOPULSE.RAW TO ROLE GEOPULSE_TEAM_ROLE;
GRANT USAGE ON FILE FORMAT GEOPULSE.RAW.PING_PARQUET
  TO ROLE GEOPULSE_TEAM_ROLE;
GRANT READ, WRITE ON STAGE GEOPULSE.RAW.PING_STAGE
  TO ROLE GEOPULSE_TEAM_ROLE;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
  ON ALL TABLES IN SCHEMA GEOPULSE.RAW TO ROLE GEOPULSE_TEAM_ROLE;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
  ON FUTURE TABLES IN SCHEMA GEOPULSE.RAW TO ROLE GEOPULSE_TEAM_ROLE;

-- Verification queries (counts are expected to be zero before loading).
SHOW TABLES IN SCHEMA GEOPULSE.RAW;
SELECT COUNT(*) AS DEVICE_PING_ROWS FROM GEOPULSE.RAW.DEVICE_PINGS;
SELECT COUNT(*) AS STORE_ROWS FROM GEOPULSE.RAW.STORES;
SELECT COUNT(*) AS ZONE_ROWS FROM GEOPULSE.RAW.ZONES;
SELECT COUNT_IF(location IS NULL) AS NULL_DEVICE_LOCATIONS
  FROM GEOPULSE.RAW.DEVICE_PINGS;
