from pathlib import Path

import pytest

from data_synthesis.load_to_snowflake import (
    REQUIRED_ENV_VARS,
    build_copy_sql,
    build_put_sql,
    build_store_merge_sql,
    build_zone_merge_sql,
    discover_parquet_files,
    load_snowflake_config,
)
from data_synthesis.pipeline_check import (
    build_bounds_sql,
    build_counts_sql,
    build_hourly_counts_sql,
    build_store_proximity_sql,
)


CONFIG = {
    "account": "example-account",
    "user": "example-user",
    "password": "example-password",
    "warehouse": "compute_wh",
    "database": "GEOPULSE",
    "schema": "RAW",
    "role": "accountadmin",
}


def valid_environment() -> dict[str, str]:
    return {
        "SNOWFLAKE_ACCOUNT": "example-account",
        "SNOWFLAKE_USER": "example-user",
        "SNOWFLAKE_PASSWORD": "example-password",
        "SNOWFLAKE_WAREHOUSE": "compute_wh",
        "SNOWFLAKE_DATABASE": "geopulse",
        "SNOWFLAKE_SCHEMA": "raw",
        "SNOWFLAKE_ROLE": "accountadmin",
    }


def test_env_validation_lists_missing_variables_without_connecting():
    with pytest.raises(ValueError) as error:
        load_snowflake_config(environ={})

    for name in REQUIRED_ENV_VARS:
        assert name in str(error.value)
    assert "example-password" not in str(error.value)


def test_env_validation_maps_values_and_normalizes_identifiers():
    config = load_snowflake_config(environ=valid_environment())

    assert config == CONFIG


def test_env_validation_rejects_unsafe_database_identifier():
    environ = valid_environment()
    environ["SNOWFLAKE_DATABASE"] = "GEOPULSE; DROP TABLE USERS"

    with pytest.raises(ValueError, match="SNOWFLAKE_DATABASE"):
        load_snowflake_config(environ=environ)


def test_file_discovery_sorts_only_numbered_parquet_parts(tmp_path: Path):
    part_two = tmp_path / "part-0002.parquet"
    part_one = tmp_path / "part-0001.parquet"
    for path in (part_two, part_one, tmp_path / "part-other.parquet"):
        path.touch()

    assert discover_parquet_files(tmp_path) == [part_one, part_two]


def test_file_discovery_explains_empty_input_directory(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="generate_pings.py"):
        discover_parquet_files(tmp_path)


def test_put_sql_uses_parallel_upload_and_only_overwrites_when_forced(
    tmp_path: Path,
):
    part = tmp_path / "part-0001.parquet"
    part.touch()

    put_sql = build_put_sql([part], "GEOPULSE.RAW.PING_STAGE")
    force_sql = build_put_sql([part], "GEOPULSE.RAW.PING_STAGE", force=True)

    assert "PARALLEL=8" in put_sql
    assert "AUTO_COMPRESS=FALSE OVERWRITE=FALSE" in put_sql
    assert "OVERWRITE=TRUE" in force_sql
    assert "@GEOPULSE.RAW.PING_STAGE" in put_sql


def test_loader_sql_matches_setup_tables_and_spatial_column_conventions():
    copy_sql = build_copy_sql(CONFIG)
    stores_sql = build_store_merge_sql(CONFIG)
    zones_sql = build_zone_merge_sql(CONFIG)

    assert "COPY INTO GEOPULSE.RAW.MOBILE_PINGS" in copy_sql
    assert "ST_MAKEPOINT($1:long::FLOAT, $1:lat::FLOAT)" in copy_sql
    assert "FORCE = FALSE" in copy_sql
    assert "ST_MAKEPOINT(source.long, source.lat)" in stores_sql
    assert "MERGE INTO GEOPULSE.RAW.COMMERCIAL_ZONES" in zones_sql
    assert "TO_GEOGRAPHY(source.geometry)" in zones_sql


def test_audit_sql_covers_counts_bounds_hourly_traffic_and_store_distance():
    assert "COALESCE(COUNT_IF(location IS NULL), 0)" in build_counts_sql(CONFIG)
    assert "DATE_PART('HOUR', timestamp_utc)" in build_hourly_counts_sql(CONFIG)
    assert "73.6" in build_bounds_sql(CONFIG)
    proximity_sql = build_store_proximity_sql(CONFIG)
    assert "ST_DWITHIN(p.location, s.location, 500)" in proximity_sql
    assert "'Store A', 'Store B'" in proximity_sql
