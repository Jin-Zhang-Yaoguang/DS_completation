from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:  # Works both as a repository-root module and as a directly executed file.
    from .build_official_manifest import (
        DEFAULT_DATES,
        build_manifest,
        production_action_hash,
    )
except ImportError:  # pragma: no cover - direct-file execution path.
    from build_official_manifest import (
        DEFAULT_DATES,
        build_manifest,
        production_action_hash,
    )


def _steps(farmer: str = "PASS", market_quantity: int = 1, count: int = 72):
    return [
        [
            {
                "action": {
                    "farmer": [farmer],
                    "hands": [["PASS"]],
                    "market": [["SELL", "WHEAT", market_quantity]],
                }
            },
            {
                "action": {"farmer": ["PASS"], "hands": [], "market": []}
            },
        ]
        for _ in range(count)
    ]


def _write_replay(path: Path, episode_id: int, seed: int, farmer: str = "PASS") -> None:
    steps = _steps(farmer=farmer, count=72)
    for step_index, step in enumerate(steps):
        status = "DONE" if step_index == len(steps) - 1 else "ACTIVE"
        reward = 100 + step_index if status == "DONE" else 0
        for row in step:
            row.update(
                {
                    "info": {},
                    "observation": {},
                    "reward": reward,
                    "status": status,
                }
            )
    payload = {
        "configuration": {"episodeSteps": 72, "seed": None},
        "id": f"uuid-{episode_id}",
        "info": {
            "EpisodeId": episode_id,
            "TeamNames": [f"A-{episode_id}", f"B-{episode_id}"],
            "seed": seed,
        },
        "module_version": "test",
        "rewards": [171, 171],
        "statuses": ["DONE", "DONE"],
        "steps": steps,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class ProductionHashTest(unittest.TestCase):
    def test_market_is_excluded_but_farmer_is_not(self) -> None:
        low_market = _steps(market_quantity=1)
        high_market = _steps(market_quantity=999)
        different_farmer = _steps(farmer="NORTH", market_quantity=1)
        self.assertEqual(
            production_action_hash(low_market, 0)[0],
            production_action_hash(high_market, 0)[0],
        )
        self.assertNotEqual(
            production_action_hash(low_market, 0)[0],
            production_action_hash(different_farmer, 0)[0],
        )

    def test_prefix72_is_exactly_indices_zero_through_seventy_one(self) -> None:
        base = _steps(count=73)
        changed = _steps(count=73)
        changed[72][0]["action"]["farmer"] = ["NORTH"]
        self.assertEqual(
            production_action_hash(base, 0, limit=72)[0],
            production_action_hash(changed, 0, limit=72)[0],
        )
        self.assertNotEqual(
            production_action_hash(base, 0)[0],
            production_action_hash(changed, 0)[0],
        )


class ManifestSmokeTest(unittest.TestCase):
    def test_build_outputs_and_seed_group_does_not_leak(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "daily"
            output = Path(temporary) / "out"
            episode_id = 1000
            for date_index, date in enumerate(DEFAULT_DATES):
                date_dir = root / date
                date_dir.mkdir(parents=True)
                for local_index in range(12):
                    seed = date_index * 100 + local_index
                    if local_index == 0:  # Same seed deliberately spans all dates.
                        seed = 7
                    _write_replay(
                        date_dir / f"{episode_id}.json",
                        episode_id=episode_id,
                        seed=seed,
                        farmer="NORTH" if local_index % 2 else "PASS",
                    )
                    episode_id += 1

            result = build_manifest(
                source_root=root,
                output_dir=output,
                dates=DEFAULT_DATES,
                min_test_unique_seeds=3,
                expected_files=36,
                progress_every=0,
            )
            self.assertTrue(result.report["data_quality_passed"])
            self.assertEqual(result.report["source"]["parsed_files"], 36)
            self.assertGreaterEqual(
                result.report["split"]["eligible_unique_seeds_by_split"]["test"], 3
            )
            repeated_seed_splits = {
                record["split"] for record in result.records if record["seed"] == 7
            }
            self.assertEqual(len(repeated_seed_splits), 1)
            self.assertTrue(result.report["split"]["leakage"]["passed"])
            for filename in (
                "official_replay_manifest.jsonl",
                "data_quality_report.json",
                "evaluation_seed_manifest.json",
                "evaluation_seed_manifest.jsonl",
            ):
                self.assertTrue((output / filename).is_file())
            structured = json.loads(
                (output / "evaluation_seed_manifest.json").read_text(encoding="utf-8")
            )
            structured_rows = {
                (row["split"], row["date"], row["seed"], row["episode_id"], row["source_relpath"])
                for split in ("train", "val", "test")
                for row in structured["splits"][split]["records"]
            }
            flat_rows = {
                (
                    row["split"],
                    row["date"],
                    row["seed"],
                    row["episode_id"],
                    row["source_relpath"],
                )
                for row in (
                    json.loads(line)
                    for line in (output / "evaluation_seed_manifest.jsonl")
                    .read_text(encoding="utf-8")
                    .splitlines()
                )
            }
            self.assertEqual(structured_rows, flat_rows)


if __name__ == "__main__":
    unittest.main()
