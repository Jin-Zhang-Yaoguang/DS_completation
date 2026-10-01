#!/usr/bin/env python3
"""V117 Replay 数据合同回归测试。"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

try:
    from .protocol import (
        EXPECTED_CONFIGURATION,
        EXPECTED_CONFIGURATION_SHA256,
        audit_replay,
        atomic_json_dump,
        extract_registered,
        lock_candidate,
        preregister,
        validate_scenario_isolation,
    )
except ImportError:
    from protocol import (
        EXPECTED_CONFIGURATION,
        EXPECTED_CONFIGURATION_SHA256,
        audit_replay,
        atomic_json_dump,
        extract_registered,
        lock_candidate,
        preregister,
        validate_scenario_isolation,
    )


SENTINEL = "PLAYER_HISTORY_MUST_NEVER_APPEAR"
ROOT = Path(__file__).resolve().parents[1]
REAL_REPLAY = (
    Path(__file__).resolve().parents[3]
    / "model_data/kaggriculture_episodes_index/date=2026-08-26/data/100148657.json"
)


def _synthetic_replay(episode_id: int, seed: int, shops: list[str]) -> dict:
    steps = []
    for step in range(8):
        visible = [] if step < 3 else shops
        steps.append(
            [
                {
                    "action": {"farmer": [SENTINEL], "hands": [], "market": []},
                    "observation": {
                        "town": {"unlocked_shops": visible},
                        "farms": [{"secret": SENTINEL}],
                        "private": {"secret": SENTINEL},
                        "market": {"secret": SENTINEL},
                    },
                    "reward": SENTINEL,
                },
                {"action": SENTINEL, "observation": {"town": {"unlocked_shops": visible}}},
            ]
        )
    return {
        "configuration": EXPECTED_CONFIGURATION,
        "info": {"EpisodeId": episode_id, "seed": seed, "Agents": [SENTINEL]},
        "module_version": "1.32.7",
        "rewards": [SENTINEL],
        "steps": steps,
    }


def _write_replay(path: Path, episode_id: int, seed: int, shops: list[str]) -> None:
    path.write_text(
        json.dumps(_synthetic_replay(episode_id, seed, shops), ensure_ascii=False),
        encoding="utf-8",
    )


def _assignment(record: dict, split: str = "development") -> dict:
    return {
        "record_id": record["record_id"],
        "source_class": record["source_class"],
        "episode_id": record["episode_id"],
        "actual_seed": record["actual_seed"],
        "observed_date": record["observed_date"],
        "replay_path": record["replay_path"],
        "replay_sha256": record["replay_sha256"],
        "configuration_sha256": record["configuration_sha256"],
        "account_lineage": record.get("account_lineage"),
        "split": split,
        "rank_sha256": "0" * 64,
        "scenario_sha256": None,
    }


def run() -> dict:
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="v117-replay-test-") as temporary:
        temp = Path(temporary)
        specs = [
            (101, 1001, "ACCOUNT_ONLINE", "2026-08-20", ["BAKERY"]),
            (102, 1002, "ACCOUNT_ONLINE", "2026-08-21", ["YARN_STORE"]),
            (103, 1003, "ACCOUNT_ONLINE", "2026-08-22", ["PET_CAFE"]),
            (201, 2001, "OFFICIAL_DAILY", "2026-08-20", ["PET_CAFE"]),
            (202, 2002, "OFFICIAL_DAILY", "2026-08-21", ["PIZZA_SHOP"]),
            (203, 2003, "OFFICIAL_DAILY", "2026-08-22", ["SMOOTHIE_SHOP"]),
        ]
        records = []
        for episode_id, seed, source, observed_date, shops in specs:
            replay_path = temp / f"{episode_id}.json"
            _write_replay(replay_path, episode_id, seed, shops)
            lineage = ({
                "submission_id": 55000000 + episode_id,
                "model_version": "v117-test-fixture",
                "seat": episode_id % 2,
                "agent_or_package_sha256": "a" * 64,
                "agent_log_sha256": "b" * 64,
            } if source == "ACCOUNT_ONLINE" else {})
            records.append(
                audit_replay(
                    replay_path,
                    source_class=source,
                    observed_date=observed_date,
                    date_basis="test_fixture",
                    episode_type="EpisodeType.EPISODE_TYPE_PUBLIC",
                    **lineage,
                )
            )
        checks["synthetic_records_strict_ready"] = all(row["strict_ready"] for row in records)
        checks["complete_configuration_hash"] = all(
            row["configuration_sha256"] == EXPECTED_CONFIGURATION_SHA256 for row in records
        )

        old_record = audit_replay(
            temp / "101.json",
            source_class="ACCOUNT_ONLINE",
            observed_date="2026-08-19",
            date_basis="test_fixture",
            episode_type="EpisodeType.EPISODE_TYPE_PUBLIC",
            submission_id=55000101,
            model_version="v117-test-fixture",
            seat=1,
            agent_or_package_sha256="a" * 64,
        )
        checks["pre_cutoff_rejected"] = (
            not old_record["strict_ready"] and "before_cutoff" in old_record["failures"]
        )
        validation_record = audit_replay(
            temp / "101.json",
            source_class="ACCOUNT_ONLINE",
            observed_date="2026-08-20",
            date_basis="test_fixture",
            episode_type="EpisodeType.EPISODE_TYPE_VALIDATION",
            submission_id=55000101,
            model_version="v117-test-fixture",
            seat=1,
            agent_or_package_sha256="a" * 64,
        )
        checks["validation_episode_excluded_from_formal_panel"] = (
            validation_record["strict_ready"]
            and not validation_record["panel_ready"]
            and validation_record["panel_exclusion"] == "not_public_match"
        )

        missing_lineage = audit_replay(
            temp / "101.json", source_class="ACCOUNT_ONLINE", observed_date="2026-08-20",
            date_basis="test_fixture", episode_type="EpisodeType.EPISODE_TYPE_PUBLIC",
        )
        checks["account_lineage_is_fail_closed"] = (
            not missing_lineage["strict_ready"]
            and "missing_submission_id" in missing_lineage["failures"]
            and "missing_or_invalid_agent_or_package_sha256" in missing_lineage["failures"]
        )

        manifest = preregister(
            records, salt="unit-test", train_per_source=1, dev_per_source=1, frozen_per_source=1,
        )
        checks["source_panels_separate"] = manifest["source_reporting"]["mix_results"] is False
        checks["latest_date_is_blind_per_source"] = all(
            split["latest_date_reserved_for_blind"]
            and split["blind_dates"] == ["2026-08-22"]
            and split["development_dates"] == ["2026-08-21"]
            and split["train_dates"] == ["2026-08-20"]
            for split in manifest["date_split"].values()
        )
        checks["account_panel_blocks_promotion"] = (
            manifest["source_reporting"]["account_failure_blocks_promotion"] is True
            and manifest["source_reporting"]["official_volume_cannot_override_account"] is True
        )
        checks["gold_gate_unchanged"] = (
            manifest["gold_gate"]["status"] == "UNCHANGED_R4_TO_R7"
            and manifest["gold_gate"]["source_specific_threshold"] is None
            and manifest["gold_gate"]["both_sources_and_gate"] is False
            and "panel_gate" not in manifest
        )
        checks["split_counts"] = all(value == 1 for value in manifest["counts"].values())

        development = next(row for row in manifest["assignments"] if row["split"] == "development")
        scenario = extract_registered(
            manifest,
            source_class=development["source_class"],
            episode_id=development["episode_id"],
        )
        scenario_json = json.dumps(scenario, ensure_ascii=False, sort_keys=True)
        checks["historical_fields_not_copied"] = SENTINEL not in scenario_json
        checks["exogenous_fields_present"] = (
            scenario["realized_public_shops"]
            and scenario["derived_town_demand"]
            and scenario["step_count"] == 8
        )

        frozen = next(row for row in manifest["assignments"] if row["split"] == "blind_confirmation")
        try:
            extract_registered(
                manifest,
                source_class=frozen["source_class"],
                episode_id=frozen["episode_id"],
            )
            checks["frozen_closed_before_lock"] = False
        except PermissionError:
            checks["frozen_closed_before_lock"] = True
        candidate_sha = "a" * 64
        locked = lock_candidate(manifest, candidate_sha)
        frozen_scenario = extract_registered(
            locked,
            source_class=frozen["source_class"],
            episode_id=frozen["episode_id"],
            candidate_sha256=candidate_sha,
        )
        checks["frozen_opens_only_for_locked_candidate"] = (
            frozen_scenario["candidate_sha256"] == candidate_sha
        )

        try:
            validate_scenario_isolation([scenario, scenario])
            checks["collision_fail_closed"] = False
        except ValueError:
            checks["collision_fail_closed"] = True

    if REAL_REPLAY.is_file():
        real_record = audit_replay(
            REAL_REPLAY,
            source_class="OFFICIAL_DAILY",
            observed_date="2026-08-26",
            date_basis="official_partition_create_time",
            episode_type="OFFICIAL_DAILY_PUBLIC",
        )
        checks["real_replay_strict_ready"] = real_record["strict_ready"]
        real_manifest = {
            "assignments": [_assignment(real_record)],
            "frozen_lock": {"status": "UNLOCKED", "candidate_sha256": None},
        }
        real_scenario = extract_registered(
            real_manifest,
            source_class="OFFICIAL_DAILY",
            episode_id=real_record["episode_id"],
        )
        real_json = json.dumps(real_scenario, ensure_ascii=False)
        checks["real_replay_external_only"] = (
            real_scenario["step_count"] == 720
            and len(real_scenario["realized_public_shops"]) == 8
            and '"action"' not in real_json
            and '"market"' not in real_json
            and '"reward"' not in real_json
        )
    else:
        checks["real_replay_strict_ready"] = False
        checks["real_replay_external_only"] = False

    result = {
        "schema": "v117-replay-protocol-test-results-v2",
        "pass": all(checks.values()),
        "checks": checks,
        "real_replay": str(REAL_REPLAY),
    }
    atomic_json_dump(result, ROOT / "replay_protocol_test_results.json")
    return result


if __name__ == "__main__":
    outcome = run()
    print(json.dumps(outcome, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if outcome["pass"] else 1)
