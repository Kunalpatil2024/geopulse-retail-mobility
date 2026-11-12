import tempfile
import unittest
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from data_synthesis.generate_pings import (
    _assign_commute_routes,
    build_parser,
    generate_dataset,
)


class GeneratePingsTests(unittest.TestCase):
    def test_route_cohorts_match_cannibalization_scenario(self):
        route_a, route_b = _assign_commute_routes(
            2_000, np.random.default_rng(42)
        )

        self.assertEqual(int(route_a.sum()), 500)
        self.assertEqual(int(route_b.sum()), 150)
        self.assertTrue((route_b <= route_a).all())

    def test_cli_defaults(self):
        args = build_parser().parse_args([])

        self.assertEqual(args.devices, 100_000)
        self.assertEqual(args.days, 7)
        self.assertEqual(args.start_date, date(2026, 11, 2))
        self.assertEqual(args.out_dir, Path("data/pings"))
        self.assertEqual(args.seed, 42)
        self.assertEqual(args.chunk_devices, 10_000)

    def test_chunked_parquet_and_sample_are_reproducible(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            outputs = []
            samples = []
            for run in ("first", "second"):
                out_dir = root / run / "pings"
                sample_path = root / run / "sample.csv"
                row_count, file_count = generate_dataset(
                    devices=100,
                    days=2,
                    start_date=date(2026, 11, 2),
                    out_dir=out_dir,
                    seed=17,
                    chunk_devices=40,
                    sample_path=sample_path,
                )
                parts = sorted(out_dir.glob("part-*.parquet"))
                self.assertEqual(file_count, 3)
                self.assertEqual(len(parts), file_count)
                self.assertEqual(
                    sum(pq.read_metadata(part).num_rows for part in parts), row_count
                )
                self.assertGreater(row_count, 1_000)
                outputs.append(
                    pd.concat([pd.read_parquet(part) for part in parts], ignore_index=True)
                    .sort_values(["device_id", "timestamp"])
                    .reset_index(drop=True)
                )
                samples.append(pd.read_csv(sample_path))

            pd.testing.assert_frame_equal(outputs[0], outputs[1])
            pd.testing.assert_frame_equal(samples[0], samples[1])
            self.assertEqual(len(samples[0]), 1_000)
            self.assertEqual(samples[0]["device_id"].nunique(), 100)
            self.assertEqual(list(samples[0].columns), ["device_id", "lat", "long", "timestamp"])
            self.assertTrue(samples[0]["device_id"].is_monotonic_increasing)
            timestamps = pd.to_datetime(outputs[0]["timestamp"], utc=True)
            night_pings = outputs[0][timestamps.dt.hour < 5]
            self.assertGreater(len(night_pings), 0)
            repeated_nights = night_pings.groupby("device_id").filter(
                lambda group: len(group) >= 2
            )
            self.assertGreater(len(repeated_nights), 0)
            first_device_nights = repeated_nights[
                repeated_nights["device_id"] == repeated_nights.iloc[0]["device_id"]
            ]
            lat_spread_m = (
                first_device_nights["lat"] - first_device_nights["lat"].mean()
            ) * 111_320
            long_spread_m = (
                first_device_nights["long"] - first_device_nights["long"].mean()
            ) * 111_320 * np.cos(np.deg2rad(first_device_nights["lat"].mean()))
            self.assertLess(np.hypot(lat_spread_m, long_spread_m).max(), 80)
            sample_times = pd.to_datetime(samples[0]["timestamp"], utc=True)
            ordered_indices = (
                samples[0]
                .assign(_timestamp=sample_times)
                .sort_values(["device_id", "_timestamp"])
                .index.tolist()
            )
            self.assertEqual(ordered_indices, list(range(1_000)))


if __name__ == "__main__":
    unittest.main()
