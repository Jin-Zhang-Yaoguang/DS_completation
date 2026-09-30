#!/usr/bin/env python3
"""Preregister the strict RC2 gate without reusing the seen random panel."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
WORKSPACE = PROJECT.parent
SOURCE = PROJECT / "model_data/failure_pattern_diagnostics_20260831/enriched_games.csv"
OUTPUT = HERE / "gate_panel_manifest_rc2.json"
LEGACY_MANIFEST = HERE / "gate_panel_manifest_rc1.json"
PARENT = HERE.parent / "v76_adjacent_safe_buy_lead/main.py"
CUTOFF = "2026-08-20"
EXPECTED_MODULE = "1.32.7"
EXPECTED_CONFIGURATION_SHA256 = "1a9006518ccbe403a70e107bb041cc2489e38da637ae0e3872500010963c46f3"
DEVELOPMENT_TARGET_SALT = "v118-development-target-v1"
DEVELOPMENT_RANDOM_SALT = "v118-development-random-v1"
FROZEN_TARGET_SALT = "v118-frozen-target-v1"
LEGACY_FROZEN_RANDOM_SALT = "v118-frozen-random-v1"
FROZEN_RANDOM_SALT = "v118-rc2-frozen-random-unseen-v1"


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _rank(row: dict[str, Any], salt: str) -> str:
    token = f"{salt}\0{row['episode_id']}"
    return hashlib.sha256(token.encode()).hexdigest()


def _canonical(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _prepare(raw: dict[str, str]) -> dict[str, Any]:
    replay_path = Path(raw["replay_path"])
    if not replay_path.is_absolute():
        replay_path = WORKSPACE / replay_path
    created_date = raw["create_time"][:10]
    if created_date < CUTOFF:
        raise ValueError(f"episode {raw['episode_id']} predates cutoff")
    if raw["module_version"] != EXPECTED_MODULE:
        raise ValueError(f"episode {raw['episode_id']} module drift")
    if raw["configuration_sha256"] != EXPECTED_CONFIGURATION_SHA256:
        raise ValueError(f"episode {raw['episode_id']} configuration drift")
    shops = raw["shop_sequence"].split(">")
    steps = [int(value) for value in raw["unlock_steps"].split(">")]
    schedule = [
        {"ordinal": index + 1, "shop": shop, "visible_from_step": step}
        for index, (shop, step) in enumerate(zip(shops, steps))
    ]
    replay_sha256 = _hash_file(replay_path)
    scenario_sha256 = _canonical({
        "module_version": EXPECTED_MODULE,
        "configuration_sha256": EXPECTED_CONFIGURATION_SHA256,
        "actual_seed": int(float(raw["seed"])),
        "realized_public_shops": schedule,
    })
    return {
        "source_class": "ACCOUNT_ONLINE",
        "source_role": "PRIMARY",
        "episode_id": int(raw["episode_id"]),
        "submission_id": int(raw["submission_id"]),
        "observed_date": created_date,
        "episode_type": raw["type"],
        "actual_seed": int(float(raw["seed"])),
        "module_version": raw["module_version"],
        "configuration_sha256": raw["configuration_sha256"],
        "replay_path": str(replay_path.resolve()),
        "replay_sha256": replay_sha256,
        "scenario_sha256": scenario_sha256,
        "yarn_position": int(float(raw["yarn_position"])),
        "realized_public_shops": schedule,
    }


def _take(pool: list[dict[str, Any]], count: int, salt: str) -> list[dict[str, Any]]:
    selected = sorted(pool, key=lambda row: _rank(row, salt))[:count]
    if len(selected) != count:
        raise ValueError(f"panel {salt} only has {len(selected)} rows; needs {count}")
    return selected


def main() -> int:
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        rows = [_prepare(row) for row in csv.DictReader(handle)]
    if len({(row["episode_id"], row["replay_sha256"]) for row in rows}) != len(rows):
        raise ValueError("duplicate episode_id + replay_sha256")

    target_pool = [row for row in rows if row["yarn_position"] in (2, 3)]
    development_target = _take(target_pool, 32, DEVELOPMENT_TARGET_SALT)
    used = {row["episode_id"] for row in development_target}
    development_random = _take(
        [row for row in rows if row["episode_id"] not in used],
        32, DEVELOPMENT_RANDOM_SALT,
    )
    used.update(row["episode_id"] for row in development_random)
    frozen_target = _take(
        [row for row in target_pool if row["episode_id"] not in used],
        64, FROZEN_TARGET_SALT,
    )
    used.update(row["episode_id"] for row in frozen_target)
    # RC1's random panel has already been observed.  Exclude it before taking
    # the RC2 random panel so the strict pure-win check remains genuinely
    # unseen.  The target panel is retained because only 39 unused target
    # account Replays remain; it stayed isolated from development and RC2's
    # random-only generalization was not selected from its outcomes.
    legacy_frozen_random = _take(
        [row for row in rows if row["episode_id"] not in used],
        64, LEGACY_FROZEN_RANDOM_SALT,
    )
    excluded_random = used | {row["episode_id"] for row in legacy_frozen_random}
    frozen_random = _take(
        [row for row in rows if row["episode_id"] not in excluded_random],
        64, FROZEN_RANDOM_SALT,
    )

    legacy = json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))
    legacy_target_ids = {
        int(row["episode_id"]) for row in legacy["assignments"]
        if row["split"] == "frozen_gate" and row["panel"] == "target_yarn_2_or_3"
    }
    legacy_all_ids = {int(row["episode_id"]) for row in legacy["assignments"]}
    if legacy_target_ids != {row["episode_id"] for row in frozen_target}:
        raise ValueError("RC2 target panel drifted from the isolated RC1 target panel")

    assignments: list[dict[str, Any]] = []
    for split, panel, panel_rows, salt in (
        ("development", "target_yarn_2_or_3", development_target, DEVELOPMENT_TARGET_SALT),
        ("development", "random", development_random, DEVELOPMENT_RANDOM_SALT),
        ("frozen_gate", "target_yarn_2_or_3", frozen_target, FROZEN_TARGET_SALT),
        ("frozen_gate", "random", frozen_random, FROZEN_RANDOM_SALT),
    ):
        for row in panel_rows:
            assignments.append({**row, "split": split, "panel": panel, "rank_sha256": _rank(row, salt)})

    for key in ("episode_id", "actual_seed", "scenario_sha256"):
        values = [row[key] for row in assignments]
        if len(values) != len(set(values)):
            raise ValueError(f"isolation collision: {key}")
    manifest = {
        "schema": "v118-v76-yarn-gate-panels-rc2-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_class": "ACCOUNT_ONLINE",
        "source_results_mixed": False,
        "cutoff_inclusive": CUTOFF,
        "expected_module_version": EXPECTED_MODULE,
        "expected_configuration_sha256": EXPECTED_CONFIGURATION_SHA256,
        "selection": {
            "outcomes_used": False,
            "historical_player_actions_used": False,
            "historical_market_trajectory_used": False,
            "algorithm": "fixed SHA256 rank after target classification from public shop sequence",
            "salts": {
                "development_target": DEVELOPMENT_TARGET_SALT,
                "development_random": DEVELOPMENT_RANDOM_SALT,
                "frozen_target": FROZEN_TARGET_SALT,
                "legacy_frozen_random_excluded": LEGACY_FROZEN_RANDOM_SALT,
                "frozen_random": FROZEN_RANDOM_SALT,
            },
        },
        "history_controls": {
            "target_panel": "RC1 isolated frozen target retained; RC2 target path changed only by mandatory coordinate/access correctness repair",
            "random_panel": "fresh 64 sources excluding every RC1 assignment",
            "legacy_assignment_count_excluded_from_new_random": len(excluded_random),
            "unused_account_target_sources_available": len({row["episode_id"] for row in target_pool} - legacy_all_ids),
        },
        "isolation_keys": ["episode_id", "actual_seed", "scenario_sha256"],
        "counts": {
            "development:target_yarn_2_or_3": 32,
            "development:random": 32,
            "frozen_gate:target_yarn_2_or_3": 64,
            "frozen_gate:random": 64,
        },
        "gate": {
            "unit": "64 Replay sources x dual seats = 128 games per panel",
            "metric": "pure_win_rate=wins/games; ties are not wins",
            "target_yarn_2_or_3_min": 0.80,
            "random_min": 0.55,
            "both_required": True,
        },
        "candidate_lock": {
            "status": "UNLOCKED", "main_sha256": None,
            "parent_main_sha256": _hash_file(PARENT),
        },
        "assignments": assignments,
    }
    OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "counts": manifest["counts"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
