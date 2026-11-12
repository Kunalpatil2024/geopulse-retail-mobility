"""Generate deterministic, synthetic mobile-device pings for Nashik."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


CITY_LAT = 19.9975
CITY_LONG = 73.7898
STORE_A = (19.9975, 73.7898)
STORE_B = (20.0010, 73.7898)
PING_COLUMNS = ("device_id", "lat", "long", "timestamp")
SLOT_MINUTES = np.concatenate(
    (
        np.array([0, 90, 180, 270], dtype=np.int16),
        np.arange(5 * 60, 23 * 60 + 1, 15, dtype=np.int16),
        np.array([23 * 60 + 30], dtype=np.int16),
    )
)
SLOT_HOURS = SLOT_MINUTES.astype(np.float64) / 60
SAMPLE_DEVICE_COUNT = 100


def _offset_coordinates(
    lat: np.ndarray | float,
    long: np.ndarray | float,
    east_m: np.ndarray,
    north_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply local east/north meter offsets to WGS84 coordinates."""
    out_lat = np.asarray(lat) + north_m / 111_320
    out_long = np.asarray(long) + east_m / (111_320 * np.cos(np.deg2rad(lat)))
    return out_lat, out_long


def _nearby_points(
    rng: np.random.Generator,
    center: tuple[float, float],
    count: int,
    spread_m: float,
) -> tuple[np.ndarray, np.ndarray]:
    return _offset_coordinates(
        center[0],
        center[1],
        rng.normal(0, spread_m, count),
        rng.normal(0, spread_m, count),
    )


def _assign_commute_routes(
    device_count: int, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Assign exact 25% Store A and 30%-of-A Store B route cohorts."""
    route_a = np.zeros(device_count, dtype=bool)
    route_b = np.zeros(device_count, dtype=bool)
    order = rng.permutation(device_count)
    a_count = round(device_count * 0.25)
    b_count = round(a_count * 0.30)
    route_a[order[:a_count]] = True
    route_b[order[:b_count]] = True
    return route_a, route_b


def _interpolate(
    hour: np.ndarray,
    start_hour: float,
    end_hour: float,
    start_lat: np.ndarray,
    start_long: np.ndarray,
    end_lat: np.ndarray,
    end_long: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    fraction = np.clip(
        (hour - start_hour) / (end_hour - start_hour), 0.0, 1.0
    )
    return (
        start_lat[:, None] + fraction[None, :] * (end_lat - start_lat)[:, None],
        start_long[:, None]
        + fraction[None, :] * (end_long - start_long)[:, None],
    )


def _daily_locations(
    hour: np.ndarray,
    weekend: bool,
    home_lat: np.ndarray,
    home_long: np.ndarray,
    work_lat: np.ndarray,
    work_long: np.ndarray,
    a_lat: np.ndarray,
    a_long: np.ndarray,
    b_lat: np.ndarray,
    b_long: np.ndarray,
    route_a: np.ndarray,
    route_b: np.ndarray,
    leisure_lat: np.ndarray,
    leisure_long: np.ndarray,
    weekend_leisure: np.ndarray,
    evening_leisure: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    device_count = len(home_lat)
    lat = np.broadcast_to(home_lat[:, None], (device_count, len(hour))).copy()
    long = np.broadcast_to(home_long[:, None], (device_count, len(hour))).copy()

    if weekend:
        outbound_lat, outbound_long = _interpolate(
            hour, 10.5, 12.0, home_lat, home_long,
            leisure_lat, leisure_long,
        )
        return_lat, return_long = _interpolate(
            hour, 15.0, 16.5, leisure_lat, leisure_long,
            home_lat, home_long,
        )
        daytime = (hour >= 10.5) & (hour <= 16.5)
        lat = np.where(
            daytime[None, :] & weekend_leisure[:, None],
            np.where(hour[None, :] <= 12.0, outbound_lat, leisure_lat[:, None]),
            lat,
        )
        long = np.where(
            daytime[None, :] & weekend_leisure[:, None],
            np.where(hour[None, :] <= 12.0, outbound_long, leisure_long[:, None]),
            long,
        )
        lat = np.where(
            (hour[None, :] >= 15.0) & weekend_leisure[:, None],
            return_lat,
            lat,
        )
        long = np.where(
            (hour[None, :] >= 15.0) & weekend_leisure[:, None],
            return_long,
            long,
        )
    else:
        direct_lat, direct_long = _interpolate(
            hour, 7.5, 9.25, home_lat, home_long, work_lat, work_long
        )
        home_to_a_lat, home_to_a_long = _interpolate(
            hour, 7.5, 8.5, home_lat, home_long, a_lat, a_long
        )
        a_to_work_lat, a_to_work_long = _interpolate(
            hour, 8.5, 9.25, a_lat, a_long, work_lat, work_long
        )
        home_to_b_lat, home_to_b_long = _interpolate(
            hour, 7.5, 8.25, home_lat, home_long, b_lat, b_long
        )
        b_to_a_lat, b_to_a_long = _interpolate(
            hour, 8.25, 8.75, b_lat, b_long, a_lat, a_long
        )
        a_to_work_b_lat, a_to_work_b_long = _interpolate(
            hour, 8.75, 9.25, a_lat, a_long, work_lat, work_long
        )
        a_route_lat = np.where(
            hour[None, :] <= 8.5, home_to_a_lat, a_to_work_lat
        )
        a_route_long = np.where(
            hour[None, :] <= 8.5, home_to_a_long, a_to_work_long
        )
        b_route_lat = np.where(
            hour[None, :] < 8.25,
            home_to_b_lat,
            np.where(hour[None, :] < 8.75, b_to_a_lat, a_to_work_b_lat),
        )
        b_route_long = np.where(
            hour[None, :] < 8.25,
            home_to_b_long,
            np.where(hour[None, :] < 8.75, b_to_a_long, a_to_work_b_long),
        )
        morning_lat = np.where(route_a[:, None], a_route_lat, direct_lat)
        morning_long = np.where(route_a[:, None], a_route_long, direct_long)
        morning_lat = np.where(route_b[:, None], b_route_lat, morning_lat)
        morning_long = np.where(route_b[:, None], b_route_long, morning_long)
        morning = (hour >= 7.5) & (hour <= 9.25)
        lat = np.where(morning[None, :], morning_lat, lat)
        long = np.where(morning[None, :], morning_long, long)
        lat = np.where((hour[None, :] > 9.25) & (hour[None, :] < 17.0),
                       work_lat[:, None], lat)
        long = np.where((hour[None, :] > 9.25) & (hour[None, :] < 17.0),
                        work_long[:, None], long)

        work_to_a_lat, work_to_a_long = _interpolate(
            hour, 17.0, 17.75, work_lat, work_long, a_lat, a_long
        )
        a_to_home_lat, a_to_home_long = _interpolate(
            hour, 17.75, 18.75, a_lat, a_long, home_lat, home_long
        )
        work_to_a_b_lat, work_to_a_b_long = _interpolate(
            hour, 17.0, 17.5, work_lat, work_long, a_lat, a_long
        )
        a_to_b_lat, a_to_b_long = _interpolate(
            hour, 17.5, 18.0, a_lat, a_long, b_lat, b_long
        )
        b_to_home_lat, b_to_home_long = _interpolate(
            hour, 18.0, 18.75, b_lat, b_long, home_lat, home_long
        )
        evening_a_lat = np.where(
            hour[None, :] <= 17.75, work_to_a_lat, a_to_home_lat
        )
        evening_a_long = np.where(
            hour[None, :] <= 17.75, work_to_a_long, a_to_home_long
        )
        evening_b_lat = np.where(
            hour[None, :] < 17.5,
            work_to_a_b_lat,
            np.where(hour[None, :] < 18.0, a_to_b_lat, b_to_home_lat),
        )
        evening_b_long = np.where(
            hour[None, :] < 17.5,
            work_to_a_b_long,
            np.where(hour[None, :] < 18.0, a_to_b_long, b_to_home_long),
        )
        evening_lat = np.where(route_a[:, None], evening_a_lat, work_lat[:, None])
        evening_long = np.where(route_a[:, None], evening_a_long, work_long[:, None])
        evening_lat = np.where(route_b[:, None], evening_b_lat, evening_lat)
        evening_long = np.where(route_b[:, None], evening_b_long, evening_long)
        evening_commute = (hour >= 17.0) & (hour <= 18.75)
        lat = np.where(evening_commute[None, :], evening_lat, lat)
        long = np.where(evening_commute[None, :], evening_long, long)

        outbound_lat, outbound_long = _interpolate(
            hour, 19.0, 20.0, home_lat, home_long, leisure_lat, leisure_long
        )
        return_lat, return_long = _interpolate(
            hour, 20.0, 21.5, leisure_lat, leisure_long, home_lat, home_long
        )
        evening_window = (hour >= 19.0) & (hour <= 21.5)
        evening_position_lat = np.where(
            hour[None, :] <= 20.0, outbound_lat, return_lat
        )
        evening_position_long = np.where(
            hour[None, :] <= 20.0, outbound_long, return_long
        )
        lat = np.where(
            evening_window[None, :] & evening_leisure[:, None],
            evening_position_lat,
            lat,
        )
        long = np.where(
            evening_window[None, :] & evening_leisure[:, None],
            evening_position_long,
            long,
        )

    return lat, long


def _new_device_locations(
    count: int, rng: np.random.Generator
) -> tuple[np.ndarray, ...]:
    home_lat, home_long = _nearby_points(rng, (CITY_LAT, CITY_LONG), count, 2600)
    commercial_lat, commercial_long = _offset_coordinates(
        CITY_LAT,
        CITY_LONG,
        np.array([0, 1600, -1100, 700]),
        np.array([0, 900, 1400, -1500]),
    )
    center_index = rng.choice(4, count, p=(0.45, 0.25, 0.18, 0.12))
    center_lat = commercial_lat[center_index]
    center_long = commercial_long[center_index]
    work_lat, work_long = _offset_coordinates(
        center_lat,
        center_long,
        rng.normal(0, 550, count),
        rng.normal(0, 550, count),
    )
    a_lat, a_long = _nearby_points(rng, STORE_A, count, 20)
    b_lat, b_long = _nearby_points(rng, STORE_B, count, 20)
    return home_lat, home_long, work_lat, work_long, a_lat, a_long, b_lat, b_long


def _generate_day(
    device_ids: np.ndarray,
    day: date,
    locations: tuple[np.ndarray, ...],
    route_a: np.ndarray,
    route_b: np.ndarray,
    sparse: np.ndarray,
    rng: np.random.Generator,
) -> pd.DataFrame:
    count = len(device_ids)
    home_lat, home_long, work_lat, work_long, a_lat, a_long, b_lat, b_long = locations
    weekend = day.weekday() >= 5
    leisure_center = _nearby_points(rng, (CITY_LAT, CITY_LONG), count, 1800)
    leisure_lat, leisure_long = leisure_center
    weekend_leisure = rng.random(count) < 0.62
    evening_leisure = rng.random(count) < 0.24

    slot_jitter = rng.integers(-2, 3, size=(count, len(SLOT_MINUTES)))
    lat, long = _daily_locations(
        SLOT_HOURS,
        weekend,
        home_lat,
        home_long,
        work_lat,
        work_long,
        a_lat,
        a_long,
        b_lat,
        b_long,
        route_a,
        route_b,
        leisure_lat,
        leisure_long,
        weekend_leisure,
        evening_leisure,
    )

    if weekend:
        probability = np.select(
            [
                (SLOT_HOURS >= 10) & (SLOT_HOURS <= 16),
                (SLOT_HOURS >= 18) & (SLOT_HOURS <= 21),
            ],
            [0.26, 0.23],
            default=0.18,
        )
    else:
        probability = np.select(
            [
                (SLOT_HOURS >= 7) & (SLOT_HOURS < 9.5),
                (SLOT_HOURS >= 9.5) & (SLOT_HOURS < 16.5),
                (SLOT_HOURS >= 16.5) & (SLOT_HOURS < 19),
                ((SLOT_HOURS >= 6) & (SLOT_HOURS < 7))
                | ((SLOT_HOURS >= 19) & (SLOT_HOURS < 22)),
            ],
            [0.68, 0.38, 0.68, 0.45],
            default=0.28,
        )
    keep = rng.random((count, len(SLOT_MINUTES))) < (
        probability[None, :] * np.where(sparse, 0.28, 1.0)[:, None]
    )
    if not weekend:
        keep[route_a, np.flatnonzero(SLOT_MINUTES == 8 * 60 + 30)[0]] = True
        b_slot = np.flatnonzero(SLOT_MINUTES == 8 * 60 + 15)[0]
        a_slot = np.flatnonzero(SLOT_MINUTES == 8 * 60 + 45)[0]
        keep[route_b, b_slot] = True
        keep[route_b, a_slot] = True

    noise_lat = rng.normal(0, 7, size=lat.shape) / 111_320
    noise_long = rng.normal(0, 7, size=long.shape) / (
        111_320 * np.cos(np.deg2rad(lat))
    )
    lat += noise_lat
    long += noise_long

    device_index, slot_index = np.nonzero(keep)
    minute_of_day = SLOT_MINUTES[slot_index] + slot_jitter[device_index, slot_index]
    timestamp = (
        pd.Timestamp(day, tz="UTC")
        + pd.to_timedelta(minute_of_day, unit="m")
    )
    return pd.DataFrame(
        {
            "device_id": device_ids[device_index],
            "lat": lat[device_index, slot_index],
            "long": long[device_index, slot_index],
            "timestamp": timestamp,
        },
        columns=PING_COLUMNS,
    )


def generate_dataset(
    devices: int = 100_000,
    days: int = 7,
    start_date: date = date(2026, 11, 2),
    out_dir: Path = Path("data/pings"),
    seed: int = 42,
    chunk_devices: int = 10_000,
    sample_path: Path | None = Path("docs/sample_pings_1000.csv"),
) -> tuple[int, int]:
    """Write chunked Parquet files and the sorted day-one CSV example."""
    if devices <= 0 or days <= 0 or chunk_devices <= 0:
        raise ValueError("devices, days, and chunk_devices must all be positive")

    out_dir.mkdir(parents=True, exist_ok=True)
    for existing in out_dir.glob("part-*.parquet"):
        existing.unlink()
    if sample_path is not None:
        sample_path.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)
    all_route_a, all_route_b = _assign_commute_routes(devices, rng)
    total_rows = 0
    files_written = 0
    sample_rows = 0
    sample_frames: list[pd.DataFrame] = []
    started = time.perf_counter()

    for chunk_start in range(0, devices, chunk_devices):
        chunk_end = min(chunk_start + chunk_devices, devices)
        count = chunk_end - chunk_start
        device_ids = np.array(
            [f"dev_{i:06d}" for i in range(chunk_start, chunk_end)], dtype=object
        )
        route_a = all_route_a[chunk_start:chunk_end]
        route_b = all_route_b[chunk_start:chunk_end]
        locations = _new_device_locations(count, rng)
        sparse = rng.random(count) < 0.12
        part_path = out_dir / f"part-{files_written + 1:04d}.parquet"
        writer: pq.ParquetWriter | None = None

        try:
            for day_offset in range(days):
                current_day = start_date + timedelta(days=day_offset)
                frame = _generate_day(
                    device_ids, current_day, locations, route_a, route_b, sparse, rng
                )
                table = pa.Table.from_pandas(frame, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(part_path, table.schema, compression="snappy")
                writer.write_table(table)
                total_rows += len(frame)
                if sample_path is not None and chunk_start < SAMPLE_DEVICE_COUNT:
                    sample_frames.append(
                        frame[
                            frame["device_id"] < f"dev_{SAMPLE_DEVICE_COUNT:06d}"
                        ].copy()
                    )
        finally:
            if writer is not None:
                writer.close()

        files_written += 1

    if sample_path is not None:
        sample = pd.concat(sample_frames, ignore_index=True)
        sample.sort_values(["device_id", "timestamp"], kind="stable", inplace=True)
        sample["_device_row"] = sample.groupby("device_id", sort=False).cumcount()
        balanced = sample[sample["_device_row"] < 10]
        if len(balanced) < 1000:
            additional = sample[sample["_device_row"] >= 10].head(
                1000 - len(balanced)
            )
            balanced = pd.concat([balanced, additional])
        sample = balanced.drop(columns="_device_row").sort_values(
            ["device_id", "timestamp"], kind="stable"
        )
        sample.to_csv(sample_path, index=False)
        sample_rows = len(sample)

    elapsed = time.perf_counter() - started
    print(
        f"Rows: {total_rows:,} | Parquet files: {files_written} | "
        f"Elapsed: {elapsed:.2f}s"
    )
    if sample_path is not None:
        print(f"Sample CSV: {sample_path} ({sample_rows:,} rows)")
    return total_rows, files_written


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("start-date must use YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devices", type=int, default=100_000)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--start-date", type=_parse_date, default=date(2026, 11, 2))
    parser.add_argument("--out-dir", type=Path, default=Path("data/pings"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--chunk-devices", type=int, default=10_000)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        generate_dataset(
            devices=args.devices,
            days=args.days,
            start_date=args.start_date,
            out_dir=args.out_dir,
            seed=args.seed,
            chunk_devices=args.chunk_devices,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
