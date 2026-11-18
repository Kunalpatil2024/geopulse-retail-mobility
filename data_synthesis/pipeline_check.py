"""Audit loaded GeoPulse data against the local synthetic Parquet dataset."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Mapping

import pyarrow.parquet as pq

from data_synthesis.load_to_snowflake import (
    DEFAULT_PING_DIR,
    REPOSITORY_ROOT,
    _qualified_name,
    connect_snowflake,
    discover_parquet_files,
    load_snowflake_config,
)


REPORT_PATH = REPOSITORY_ROOT / "docs" / "pipeline_audit.md"
CITY_BOUNDS = {
    "min_lat": 19.85,
    "max_lat": 20.15,
    "min_long": 73.60,
    "max_long": 74.00,
}


def count_local_parquet_rows(files: list[Path]) -> int:
    return sum(pq.read_metadata(path).num_rows for path in files)


def build_counts_sql(config: Mapping[str, str]) -> str:
    table = _qualified_name(config, "DEVICE_PINGS")
    return (
        f"SELECT COUNT(*), COALESCE(COUNT_IF(location IS NULL), 0) "
        f"FROM {table}"
    )


def build_hourly_counts_sql(config: Mapping[str, str]) -> str:
    table = _qualified_name(config, "DEVICE_PINGS")
    return (
        f"SELECT DATE_PART('HOUR', timestamp_utc)::INTEGER AS hour_of_day, "
        f"COUNT(*) AS ping_count FROM {table} "
        "GROUP BY hour_of_day ORDER BY hour_of_day"
    )


def build_bounds_sql(config: Mapping[str, str]) -> str:
    table = _qualified_name(config, "DEVICE_PINGS")
    bounds = CITY_BOUNDS
    return f"""SELECT COALESCE(COUNT_IF(
  lat < {bounds['min_lat']} OR lat > {bounds['max_lat']}
  OR long < {bounds['min_long']} OR long > {bounds['max_long']}
), 0)
FROM {table}"""


def build_store_proximity_sql(config: Mapping[str, str]) -> str:
    pings = _qualified_name(config, "DEVICE_PINGS")
    stores = _qualified_name(config, "STORES")
    return f"""SELECT s.store_name,
  COUNT_IF(ST_DWITHIN(p.location, s.location, 500)) AS nearby_pings
FROM {stores} AS s
CROSS JOIN {pings} AS p
WHERE s.store_name IN ('Store A', 'Store B')
GROUP BY s.store_name"""


def build_cannibalization_sql(config: Mapping[str, str]) -> str:
    pings = _qualified_name(config, "DEVICE_PINGS")
    stores = _qualified_name(config, "STORES")
    return f"""SELECT
  COUNT_IF(visited_a AND visited_b) AS shared_devices,
  COUNT_IF(visited_a) AS store_a_devices
FROM (
  SELECT p.device_id,
    COUNT_IF(s.store_name = 'Store A'
      AND DATE_PART('MINUTE', p.timestamp_utc)::INTEGER BETWEEN 28 AND 32
      AND ST_DWITHIN(p.location, s.location, 500)) > 0 AS visited_a,
    COUNT_IF(s.store_name = 'Store B'
      AND DATE_PART('MINUTE', p.timestamp_utc)::INTEGER BETWEEN 13 AND 17
      AND ST_DWITHIN(p.location, s.location, 500)) > 0 AS visited_b
  FROM {pings} AS p
  CROSS JOIN {stores} AS s
  WHERE s.store_name IN ('Store A', 'Store B')
    AND DATE_PART('DOWISO', p.timestamp_utc)::INTEGER BETWEEN 1 AND 5
    AND DATE_PART('HOUR', p.timestamp_utc)::INTEGER = 8
    AND DATE_PART('MINUTE', p.timestamp_utc)::INTEGER BETWEEN 13 AND 32
  GROUP BY p.device_id
)"""


def _cannibalization_result(
    shared_devices: int, store_a_devices: int
) -> tuple[str, bool, str]:
    share = shared_devices / store_a_devices if store_a_devices else 0.0
    return (
        "Store B overlap with Store A morning commuters (30% +/- 5%)",
        store_a_devices > 0 and 0.25 <= share <= 0.35,
        (
            f"{shared_devices:,} of {store_a_devices:,} Store A devices at "
            f"08:28-08:32 also visited Store B at 08:13-08:17 ({share:.1%}; "
            f"expected 25.0%-35.0%)."
        ),
    )


def _format_audit(
    results: list[tuple[str, bool, str]],
    local_rows: int,
    generated_at: datetime,
) -> str:
    lines = [
        "# GeoPulse pipeline audit",
        "",
        f"Generated: {generated_at.astimezone(timezone.utc).isoformat()}",
        f"Local Parquet rows: {local_rows:,}",
        "",
        "| Check | Result | Details |",
        "|---|---|---|",
    ]
    for name, passed, details in results:
        status = "PASS" if passed else "FAIL"
        lines.append(f"| {name} | **{status}** | {details} |")
    lines.append("")
    return "\n".join(lines)


def run_audit(
    config: Mapping[str, str],
    files: list[Path],
    report_path: Path = REPORT_PATH,
) -> list[tuple[str, bool, str]]:
    local_rows = count_local_parquet_rows(files)
    connection = connect_snowflake(config)
    try:
        with connection.cursor() as cursor:
            cursor.execute(build_counts_sql(config))
            snowflake_rows, null_locations = map(int, cursor.fetchone())

            cursor.execute(build_hourly_counts_sql(config))
            hourly_counts = {int(hour): int(count) for hour, count in cursor.fetchall()}

            cursor.execute(build_bounds_sql(config))
            outside_bounds = int(cursor.fetchone()[0] or 0)

            cursor.execute(build_store_proximity_sql(config))
            store_counts = {name: int(count) for name, count in cursor.fetchall()}

            cursor.execute(build_cannibalization_sql(config))
            shared_devices, store_a_devices = map(int, cursor.fetchone())
    finally:
        connection.close()

    night_hours = range(0, 6)
    night_average = sum(hourly_counts.get(hour, 0) for hour in night_hours) / len(
        night_hours
    )
    morning_average = sum(hourly_counts.get(hour, 0) for hour in (8, 9)) / 2
    evening_average = sum(hourly_counts.get(hour, 0) for hour in (17, 18)) / 2

    results = [
        (
            "Parquet and Snowflake row counts match",
            snowflake_rows == local_rows,
            f"Snowflake {snowflake_rows:,}; local {local_rows:,}.",
        ),
        (
            "No NULL LOCATION values",
            null_locations == 0,
            f"{null_locations:,} NULL locations.",
        ),
        (
            "Morning and evening traffic exceed night",
            morning_average > night_average and evening_average > night_average,
            (
                f"Average pings/hour: morning (8-9) {morning_average:.1f}, "
                f"evening (17-18) {evening_average:.1f}, "
                f"night (00-05) {night_average:.1f}."
            ),
        ),
        (
            "Pings are within the Nashik city bounding box",
            outside_bounds == 0,
            f"{outside_bounds:,} pings outside "
            f"lat [{CITY_BOUNDS['min_lat']}, {CITY_BOUNDS['max_lat']}], "
            f"long [{CITY_BOUNDS['min_long']}, {CITY_BOUNDS['max_long']}].",
        ),
        (
            "Store A and Store B each have pings within 500 m",
            store_counts.get("Store A", 0) > 0
            and store_counts.get("Store B", 0) > 0,
            (
                f"Store A: {store_counts.get('Store A', 0):,}; "
                f"Store B: {store_counts.get('Store B', 0):,}."
            ),
        ),
        _cannibalization_result(shared_devices, store_a_devices),
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _format_audit(results, local_rows, datetime.now(timezone.utc)),
        encoding="utf-8",
    )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ping-dir", type=Path, default=DEFAULT_PING_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started = time.perf_counter()
    try:
        config = load_snowflake_config()
        files = discover_parquet_files(args.ping_dir)
        results = run_audit(config, files, args.report)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc

    for name, passed, details in results:
        print(f"{'PASS' if passed else 'FAIL'}: {name} - {details}")
    print(f"Audit report: {args.report}")
    print(f"Audit time: {time.perf_counter() - started:.2f}s")
    return 0 if all(passed for _, passed, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
