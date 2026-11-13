"""Load generated GeoPulse data into the Snowflake raw tables."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import time
from typing import Mapping

from dotenv import load_dotenv


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PING_DIR = REPOSITORY_ROOT / "data" / "pings"
STORES_PATH = REPOSITORY_ROOT / "docs" / "store_locations.csv"
ZONES_PATH = REPOSITORY_ROOT / "docs" / "commercial_zones.geojson"
REQUIRED_ENV_VARS = (
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA",
    "SNOWFLAKE_ROLE",
)


def load_snowflake_config(
    env_file: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Load and validate connector options without exposing credential values."""
    if environ is None:
        load_dotenv(env_file or REPOSITORY_ROOT / ".env")
        environ = os.environ

    missing = [name for name in REQUIRED_ENV_VARS if not environ.get(name, "").strip()]
    if missing:
        raise ValueError(
            "Missing required Snowflake environment variables: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill in each value."
        )

    for name in ("SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA"):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", environ[name].strip()):
            raise ValueError(f"{name} must be a simple Snowflake identifier.")

    return {
        "account": environ["SNOWFLAKE_ACCOUNT"].strip(),
        "user": environ["SNOWFLAKE_USER"].strip(),
        "password": environ["SNOWFLAKE_PASSWORD"],
        "warehouse": environ["SNOWFLAKE_WAREHOUSE"].strip(),
        "database": environ["SNOWFLAKE_DATABASE"].strip().upper(),
        "schema": environ["SNOWFLAKE_SCHEMA"].strip().upper(),
        "role": environ["SNOWFLAKE_ROLE"].strip(),
    }


def connect_snowflake(config: Mapping[str, str]):
    """Connect to Snowflake and report connection failures without secrets."""
    import snowflake.connector

    try:
        return snowflake.connector.connect(**config)
    except Exception as exc:
        raise RuntimeError(
            "Snowflake connection failed. Check the account, user, password, "
            "warehouse, database, schema, role, and network access."
        ) from exc


def discover_parquet_files(ping_dir: Path = DEFAULT_PING_DIR) -> list[Path]:
    """Find the generator's numbered Parquet parts, in stable load order."""
    files = sorted(
        path
        for path in ping_dir.glob("part-*.parquet")
        if re.fullmatch(r"part-\d{4}\.parquet", path.name)
    )
    if not files:
        raise FileNotFoundError(
            f"No part-*.parquet files found in {ping_dir}. "
            "Run data_synthesis/generate_pings.py first."
        )
    return files


def _qualified_name(config: Mapping[str, str], object_name: str) -> str:
    return f"{config['database']}.{config['schema']}.{object_name}"


def build_put_sql(
    files: list[Path], stage: str, force: bool = False, parallel: int = 8
) -> str:
    """Build the Snowflake PUT command for the Parquet part directory."""
    if not files:
        raise ValueError("At least one Parquet file is required for PUT.")
    if parallel < 1:
        raise ValueError("PUT parallelism must be at least one.")
    source_pattern = files[0].parent.resolve().as_uri() + "/part-*.parquet"
    quoted_pattern = source_pattern.replace("'", "''")
    return (
        f"PUT '{quoted_pattern}' @{stage} PARALLEL={parallel} "
        f"AUTO_COMPRESS=FALSE OVERWRITE={'TRUE' if force else 'FALSE'}"
    )


def build_copy_sql(config: Mapping[str, str], force: bool = False) -> str:
    """Build a COPY that maps the generator schema and makes longitude-first points."""
    database = config["database"]
    schema = config["schema"]
    stage = _qualified_name(config, "PING_STAGE")
    file_format = _qualified_name(config, "PING_PARQUET")
    return f"""COPY INTO {database}.{schema}.MOBILE_PINGS
  (device_id, lat, long, timestamp_utc, location)
FROM (
  SELECT
    $1:device_id::STRING,
    $1:lat::FLOAT,
    $1:long::FLOAT,
    $1:timestamp::TIMESTAMP_TZ,
    ST_MAKEPOINT($1:long::FLOAT, $1:lat::FLOAT)
  FROM @{stage}
)
FILE_FORMAT = (FORMAT_NAME = '{file_format}')
PATTERN = '.*part-[0-9]{{4}}[.]parquet'
ON_ERROR = 'ABORT_STATEMENT'
FORCE = {'TRUE' if force else 'FALSE'}"""


def build_store_merge_sql(config: Mapping[str, str]) -> str:
    target = _qualified_name(config, "STORES")
    return f"""MERGE INTO {target} AS target
USING STORES_INPUT AS source
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
)"""


def build_zone_merge_sql(config: Mapping[str, str]) -> str:
    target = _qualified_name(config, "COMMERCIAL_ZONES")
    return f"""MERGE INTO {target} AS target
USING ZONES_INPUT AS source
ON target.zone_id = source.zone_id
WHEN MATCHED THEN UPDATE SET
  zone_name = source.zone_name, zone_type = source.zone_type,
  boundary = TO_GEOGRAPHY(source.geometry)
WHEN NOT MATCHED THEN INSERT (zone_id, zone_name, zone_type, boundary)
VALUES (
  source.zone_id, source.zone_name, source.zone_type,
  TO_GEOGRAPHY(source.geometry)
)"""


def _load_reference_data(connection, config: Mapping[str, str]) -> None:
    import pandas as pd
    from snowflake.connector.pandas_tools import write_pandas

    stores = pd.read_csv(STORES_PATH)
    zones_document = json.loads(ZONES_PATH.read_text(encoding="utf-8"))
    zones = pd.DataFrame(
        [
            {
                **feature["properties"],
                "geometry": json.dumps(feature["geometry"], separators=(",", ":")),
            }
            for feature in zones_document["features"]
        ]
    )

    for name, frame in (("STORES_INPUT", stores), ("ZONES_INPUT", zones)):
        success, _, _, _ = write_pandas(
            connection,
            frame,
            name,
            database=config["database"],
            schema=config["schema"],
            auto_create_table=True,
            table_type="temporary",
            quote_identifiers=False,
        )
        if not success:
            raise RuntimeError(f"Failed to stage local reference data for {name}.")

    with connection.cursor() as cursor:
        cursor.execute(build_store_merge_sql(config))
        cursor.execute(build_zone_merge_sql(config))


def load_data(
    config: Mapping[str, str],
    files: list[Path],
    truncate: bool,
    force: bool,
) -> dict[str, int]:
    """Upload Parquet parts and merge local store and zone reference data."""
    import snowflake.connector

    connection = connect_snowflake(config)
    try:
        stage = _qualified_name(config, "PING_STAGE")
        with connection.cursor() as cursor:
            if truncate:
                for table in ("MOBILE_PINGS", "STORES", "COMMERCIAL_ZONES"):
                    cursor.execute(
                        f"TRUNCATE TABLE {_qualified_name(config, table)}"
                    )
            cursor.execute(build_put_sql(files, stage, force=force))
            cursor.execute(build_copy_sql(config, force=force or truncate))

        _load_reference_data(connection, config)
        counts = {}
        with connection.cursor() as cursor:
            for table in ("MOBILE_PINGS", "STORES", "COMMERCIAL_ZONES"):
                cursor.execute(
                    f"SELECT COUNT(*) FROM {_qualified_name(config, table)}"
                )
                counts[table] = int(cursor.fetchone()[0])
        return counts
    except snowflake.connector.Error as exc:
        raise RuntimeError(f"Snowflake load failed: {exc}") from exc
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ping-dir", type=Path, default=DEFAULT_PING_DIR)
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate all three raw tables before loading.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite staged files and reload them even if Snowflake recorded them.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started = time.perf_counter()
    try:
        config = load_snowflake_config()
        files = discover_parquet_files(args.ping_dir)
        counts = load_data(config, files, truncate=args.truncate, force=args.force)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc

    print("Snowflake row counts:")
    for table, count in counts.items():
        print(f"  {table}: {count:,}")
    print(f"Total load time: {time.perf_counter() - started:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
