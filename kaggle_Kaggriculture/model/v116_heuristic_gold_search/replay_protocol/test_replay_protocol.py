from __future__ import annotations

import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import audit_registry
import scenario_extractor
import split_protocol
import targeted_admission
from stream_whitelist import ReplayFormatError, read_replay_whitelist


def replay_object(shops_by_step: list[list[str]], *, episode_id: int = 42, seed: int = 123) -> dict:
    steps = []
    for shops in shops_by_step:
        steps.append(
            [
                {
                    "action": {"secret": "ACTION_SENTINEL"},
                    "reward": "REWARD_SENTINEL",
                    "observation": {
                        "town": {"unlocked_shops": shops, "ignored": "TOWN_SENTINEL"},
                        "farms": "FARMS_SENTINEL",
                        "private": "PRIVATE_SENTINEL",
                        "market": "MARKET_SENTINEL",
                    },
                },
                {
                    "action": "OTHER_SEAT_ACTION_SENTINEL",
                    "observation": {"town": {"unlocked_shops": ["PET_CAFE"]}},
                },
            ]
        )
    return {
        "configuration": audit_registry.EXPECTED_CONFIGURATION,
        "description": "ignored",
        "info": {"EpisodeId": episode_id, "seed": seed, "TeamNames": ["forbidden"]},
        "module_version": audit_registry.EXPECTED_MODULE,
        "rewards": [1, 2],
        "steps": steps,
        "title": "synthetic",
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")


def write_account_snapshot(path: Path, submission_ids: list[int]) -> None:
    write_json(
        path,
        {
            "schema": audit_registry.ACCOUNT_SNAPSHOT_SCHEMA,
            "competition": "kaggriculture",
            "verified_at": "2026-08-30",
            "verification_command": (
                "kaggle competitions submissions kaggriculture --format json --page-size 200"
            ),
            "submission_ids": submission_ids,
            "excluded_sensitive_or_outcome_fields": ["username", "token", "score"],
        },
    )


class StreamWhitelistTests(unittest.TestCase):
    def test_metadata_reader_stops_before_invalid_steps_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "replay.json"
            prefix = {
                "configuration": audit_registry.EXPECTED_CONFIGURATION,
                "info": {"EpisodeId": 7, "seed": 11},
                "module_version": audit_registry.EXPECTED_MODULE,
            }
            text = json.dumps(prefix, separators=(",", ":"))[:-1] + ',"steps":THIS_IS_NOT_JSON}'
            path.write_text(text, encoding="utf-8")
            result = read_replay_whitelist(path, include_steps=False)
            self.assertTrue(result.stopped_before_steps)
            self.assertEqual(result.episode_id, 7)
            self.assertIsNone(result.shops_by_step)

    def test_extractor_materialises_only_public_shop_whitelist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "replay.json"
            write_json(path, replay_object([[], [], ["YARN_STORE"], ["YARN_STORE"], ["YARN_STORE"]]))
            result = scenario_extractor.extract_scenario(path)
            rendered = json.dumps(result, sort_keys=True)
            for sentinel in (
                "ACTION_SENTINEL",
                "REWARD_SENTINEL",
                "FARMS_SENTINEL",
                "PRIVATE_SENTINEL",
                "MARKET_SENTINEL",
                "OTHER_SEAT_ACTION_SENTINEL",
            ):
                self.assertNotIn(sentinel, rendered)
            self.assertEqual(result["causal_class"], "protocol_fixed_realized_rng_coupled")
            self.assertEqual(result["realized_public_shops"][0]["visible_from_step"], 2)
            event4 = next(event for event in result["derived_demand"] if event["step"] == 4)
            self.assertEqual(event4["shop_quantities"], {"WOOL": 2})
            self.assertEqual(result["forbidden_fields_materialized"], False)

    def test_non_monotone_shop_sequence_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "replay.json"
            write_json(path, replay_object([["PET_CAFE"], []]))
            with self.assertRaises(ReplayFormatError):
                scenario_extractor.extract_scenario(path)


class RegistryTests(unittest.TestCase):
    def test_metadata_registry_never_requires_valid_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invalid_replay = (
                json.dumps(
                    {
                        "configuration": audit_registry.EXPECTED_CONFIGURATION,
                        "info": {"EpisodeId": 100, "seed": 500},
                        "module_version": audit_registry.EXPECTED_MODULE,
                    },
                    separators=(",", ":"),
                )[:-1]
                + ',"steps":INVALID}'
            )
            a = root / "v_test"
            a.mkdir()
            write_json(
                a / "episodes.json",
                [
                    {
                        "id": 100,
                        "createTime": "2026-08-20T01:00:00",
                        "endTime": "2026-08-20T01:01:00",
                    }
                ],
            )
            write_json(
                a / "sync_manifest.json",
                {
                    "submission_id": 1,
                    "results": [
                        {"episode_id": 100, "kind": "replay", "status": "downloaded", "sha256": "a" * 64}
                    ],
                },
            )
            replay_path = a / "replays" / "episode-100-replay.json"
            replay_path.parent.mkdir()
            replay_path.write_text(invalid_replay, encoding="utf-8")

            b = root / "kaggriculture_episodes_index" / "date=2026-08-20" / "data"
            b.mkdir(parents=True)
            (b / "manifest.csv").write_text(
                "episode_id,create_time\n200,2026-08-20T02:00:00\n", encoding="utf-8"
            )
            b_replay = invalid_replay.replace('"EpisodeId":100', '"EpisodeId":200').replace(
                '"seed":500', '"seed":600'
            )
            (b / "200.json").write_text(b_replay, encoding="utf-8")

            snapshot = root / "account_submissions.json"
            write_account_snapshot(snapshot, [1])
            registry = audit_registry.build_registry(
                root, account_submissions_snapshot=snapshot
            )
            self.assertEqual(registry["summary"]["metadata_ready_by_source"]["A_ACCOUNT_ONLINE"], 1)
            self.assertEqual(registry["summary"]["metadata_ready_by_source"]["B_OFFICIAL_DAILY"], 1)
            self.assertEqual(sum(row["strict_ready"] for row in registry["records"]), 0)
            self.assertTrue(all(row["metadata_stopped_before_steps"] for row in registry["records"]))
            a_record = next(
                row for row in registry["records"] if row["source_class"] == "A_ACCOUNT_ONLINE"
            )
            self.assertTrue(a_record["account_submission_whitelisted"])
            self.assertEqual(
                registry["account_submission_provenance"]["status"],
                "LOADED_EXPLICIT_SNAPSHOT",
            )

    def test_account_source_without_explicit_snapshot_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "looks_like_account_data"
            a.mkdir()
            write_json(
                a / "episodes.json",
                [{"id": 101, "createTime": "2026-08-20T01:00:00"}],
            )
            write_json(a / "sync_manifest.json", {"submission_id": 123, "results": []})
            replay_path = a / "replays" / "episode-101-replay.json"
            write_json(replay_path, replay_object([[]], episode_id=101, seed=501))

            registry = audit_registry.build_registry(root)
            record = registry["records"][0]
            self.assertFalse(record["metadata_ready"])
            self.assertFalse(record["strict_ready"])
            self.assertIn("account_submission_snapshot_missing", record["failures"])
            self.assertEqual(
                registry["account_submission_provenance"]["status"],
                "MISSING_FAIL_CLOSED",
            )

    def test_account_source_submission_not_in_snapshot_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "local_submission_copy"
            a.mkdir()
            write_json(
                a / "episodes.json",
                [{"id": 102, "createTime": "2026-08-20T01:00:00"}],
            )
            write_json(a / "sync_manifest.json", {"submission_id": 999, "results": []})
            replay_path = a / "replays" / "episode-102-replay.json"
            write_json(replay_path, replay_object([[]], episode_id=102, seed=502))
            snapshot = root / "snapshot.json"
            write_account_snapshot(snapshot, [123])

            registry = audit_registry.build_registry(
                root, account_submissions_snapshot=snapshot
            )
            record = registry["records"][0]
            self.assertFalse(record["metadata_ready"])
            self.assertIn("account_submission_not_whitelisted", record["failures"])
            self.assertFalse(record["account_submission_whitelisted"])

    def test_invalid_account_snapshot_is_rejected_before_scanning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / "snapshot.json"
            write_json(
                snapshot,
                {
                    "schema": "wrong-schema",
                    "competition": "kaggriculture",
                    "verified_at": "2026-08-30",
                    "verification_command": "command",
                    "submission_ids": [1],
                },
            )
            with self.assertRaisesRegex(ValueError, "unsupported schema"):
                audit_registry.build_registry(
                    root, account_submissions_snapshot=snapshot
                )


class SplitAndLockTests(unittest.TestCase):
    @staticmethod
    def record(source: str, episode_id: int, seed: int) -> dict:
        return {
            "record_id": f"{source}:{episode_id}",
            "source_class": source,
            "episode_id": episode_id,
            "partition_date": "2026-08-20",
            "actual_seed": seed,
            "metadata_ready": True,
            "strict_ready": False,
            "replay_sha256": None,
            "sha_state": "pending",
        }

    def test_preregister_is_source_separated_and_excludes_seed_collisions(self) -> None:
        records = [
            self.record("A_ACCOUNT_ONLINE", 1, 1),
            self.record("A_ACCOUNT_ONLINE", 2, 2),
            self.record("A_ACCOUNT_ONLINE", 3, 9),
            self.record("A_ACCOUNT_ONLINE", 4, 9),
            self.record("B_OFFICIAL_DAILY", 5, 5),
            self.record("B_OFFICIAL_DAILY", 6, 6),
        ]
        manifest = split_protocol.preregister(
            {"schema": "test", "records": records}, salt="test", dev_per_source=1, frozen_per_source=1
        )
        self.assertEqual(manifest["counts"]["A_ACCOUNT_ONLINE:dev"], 1)
        self.assertEqual(manifest["counts"]["A_ACCOUNT_ONLINE:frozen"], 1)
        self.assertEqual(manifest["counts"]["B_OFFICIAL_DAILY:dev"], 1)
        self.assertEqual(manifest["counts"]["B_OFFICIAL_DAILY:frozen"], 1)
        self.assertEqual(manifest["frozen_lock"]["status"], "UNLOCKED")
        self.assertTrue(any(row["kind"] == "seed_collision" for row in manifest["exclusions"]))

    def test_frozen_guard_runs_before_replay_extractor(self) -> None:
        registry = {
            "records": [
                {
                    **self.record("A_ACCOUNT_ONLINE", 10, 10),
                    "replay_path": "/must/not/be/opened.json",
                    "strict_ready": True,
                    "sha_state": "recomputed",
                    "replay_sha256": "e" * 64,
                }
            ]
        }
        manifest = {
            "frozen_lock": {"status": "UNLOCKED", "candidate_sha256": None},
            "assignments": [
                {"source_class": "A_ACCOUNT_ONLINE", "episode_id": 10, "split": "frozen"}
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            manifest_path = Path(tmp) / "manifest.json"
            write_json(registry_path, registry)
            write_json(manifest_path, manifest)
            with mock.patch.object(scenario_extractor, "extract_scenario") as extractor:
                with self.assertRaises(PermissionError):
                    scenario_extractor.extract_registered(
                        registry_path,
                        manifest_path,
                        source_class="A_ACCOUNT_ONLINE",
                        episode_id=10,
                    )
                extractor.assert_not_called()

    def test_dev_also_requires_recomputed_replay_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            replay = root / "pending.json"
            replay.write_text("{}", encoding="utf-8")
            registry = {
                "records": [{
                    **self.record("A_ACCOUNT_ONLINE", 9, 99),
                    "replay_path": str(replay),
                }]
            }
            manifest = {
                "assignments": [{
                    "source_class": "A_ACCOUNT_ONLINE",
                    "episode_id": 9,
                    "split": "dev",
                }],
                "frozen_lock": {"status": "UNLOCKED", "candidate_sha256": None},
            }
            registry_path = root / "registry.json"
            manifest_path = root / "manifest.json"
            write_json(registry_path, registry)
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(PermissionError, "strict-ready"):
                scenario_extractor.extract_registered(
                    registry_path,
                    manifest_path,
                    source_class="A_ACCOUNT_ONLINE",
                    episode_id=9,
                )

    def test_scenario_hash_collision_fails_closed(self) -> None:
        manifest = {
            "assignments": [
                {"source_class": "A_ACCOUNT_ONLINE", "episode_id": 1},
                {"source_class": "B_OFFICIAL_DAILY", "episode_id": 2},
            ]
        }
        scenarios = [
            {
                "source_class": "A_ACCOUNT_ONLINE",
                "episode_id": 1,
                "actual_seed": 1,
                "scenario_sha256": "f" * 64,
            },
            {
                "source_class": "B_OFFICIAL_DAILY",
                "episode_id": 2,
                "actual_seed": 2,
                "scenario_sha256": "f" * 64,
            },
        ]
        with self.assertRaisesRegex(ValueError, "scenario hash collision"):
            split_protocol.validate_extracted_scenarios(manifest, scenarios)


class TargetedAdmissionTests(unittest.TestCase):
    @staticmethod
    def make_replay(path: Path, *, episode_id: int, seed: int, suffix: str = "") -> str:
        prefix = {
            "configuration": audit_registry.EXPECTED_CONFIGURATION,
            "info": {"EpisodeId": episode_id, "seed": seed},
            "module_version": audit_registry.EXPECTED_MODULE,
            "tag": suffix,
        }
        # Invalid JSON after the steps key proves that targeted admission does
        # not parse steps.  Raw-byte SHA256 still covers the complete file.
        text = json.dumps(prefix, separators=(",", ":"))[:-1] + ',"steps":NOT_PARSED}'
        path.write_text(text, encoding="utf-8")
        return targeted_admission._sha256_file(path)

    @staticmethod
    def record(
        source: str,
        episode_id: int,
        seed: int,
        replay_path: Path,
        *,
        claim: str | None = None,
    ) -> dict:
        return {
            "record_id": f"{source}:{episode_id}",
            "source_class": source,
            "episode_id": episode_id,
            "partition_date": "2026-08-20",
            "actual_seed": seed,
            "replay_path": str(replay_path),
            "metadata_ready": True,
            "metadata_stopped_before_steps": True,
            "module_version": audit_registry.EXPECTED_MODULE,
            "configuration": audit_registry.EXPECTED_CONFIGURATION,
            "configuration_sha256": audit_registry.EXPECTED_CONFIG_SHA256,
            "manifest_sha256_claim": claim,
            "replay_sha256": None,
            "sha_state": "pending_manifest_claim" if claim else "pending_unhashed",
            "strict_ready": False,
            "failures": [],
        }

    @staticmethod
    def assignment(record: dict, split: str) -> dict:
        return {
            "record_id": record["record_id"],
            "source_class": record["source_class"],
            "episode_id": record["episode_id"],
            "partition_date": record["partition_date"],
            "actual_seed": record["actual_seed"],
            "replay_sha256": None,
            "sha_state": record["sha_state"],
            "strict_ready_at_preregistration": False,
            "split": split,
        }

    @staticmethod
    def inputs(records: list[dict], splits: list[str]) -> tuple[dict, dict]:
        assignments = [
            TargetedAdmissionTests.assignment(record, split)
            for record, split in zip(records, splits, strict=True)
        ]
        counts = Counter(
            f"{row['source_class']}:{row['split']}" for row in assignments
        )
        registry = {
            "schema": audit_registry.SCHEMA,
            "expected_module_version": audit_registry.EXPECTED_MODULE,
            "expected_configuration_sha256": audit_registry.EXPECTED_CONFIG_SHA256,
            "records": records,
            "summary": {},
        }
        manifest = {
            "schema": split_protocol.SCHEMA,
            "counts": {
                f"{source}:{split}": counts[f"{source}:{split}"]
                for source in split_protocol.SOURCES
                for split in ("dev", "frozen")
            },
            "assignments": assignments,
            "frozen_lock": {"status": "UNLOCKED", "candidate_sha256": None},
        }
        return registry, manifest

    def test_plan_mode_never_opens_or_hashes_replays(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            replay_path = Path(tmp) / "not-opened.json"
            replay_path.write_text("DO NOT OPEN", encoding="utf-8")
            record = self.record("A_ACCOUNT_ONLINE", 1, 101, replay_path)
            registry, manifest = self.inputs([record], ["dev"])
            with mock.patch.object(
                targeted_admission, "_sha256_file", side_effect=AssertionError("hashed")
            ), mock.patch.object(
                targeted_admission,
                "read_replay_whitelist",
                side_effect=AssertionError("opened"),
            ):
                plan = targeted_admission.plan_admission(registry, manifest)
            self.assertEqual(plan["status"], "PLAN_ONLY_NOT_FINALIZED")
            self.assertEqual(plan["required_max_files"], 1)
            self.assertEqual(plan["files_opened"], 0)

    def test_execute_admits_every_assignment_and_checks_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a_path = root / "a.json"
            b_path = root / "b.json"
            a_sha = self.make_replay(a_path, episode_id=11, seed=101, suffix="a")
            b_sha = self.make_replay(b_path, episode_id=22, seed=202, suffix="b")
            records = [
                self.record("A_ACCOUNT_ONLINE", 11, 101, a_path, claim=a_sha),
                self.record("B_OFFICIAL_DAILY", 22, 202, b_path),
            ]
            registry, manifest = self.inputs(records, ["dev", "frozen"])
            admitted_registry, admitted_split, result = targeted_admission.finalize_admission(
                registry, manifest, max_files=2
            )
            self.assertEqual(result["status"], "FINALIZED_ALL_ASSIGNMENTS_STRICT_READY")
            self.assertEqual(result["files_hashed"], 2)
            self.assertFalse(result["steps_parsed"])
            self.assertEqual(
                {row["replay_sha256"] for row in admitted_registry["records"]},
                {a_sha, b_sha},
            )
            self.assertTrue(all(row["strict_ready"] for row in admitted_registry["records"]))
            self.assertTrue(all(row["strict_ready"] for row in admitted_split["assignments"]))
            self.assertTrue(
                all(row["sha_state"] == "recomputed" for row in admitted_split["assignments"])
            )

    def test_execute_requires_exact_full_assignment_limit_before_hashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "one.json"
            self.make_replay(path, episode_id=1, seed=1)
            record = self.record("A_ACCOUNT_ONLINE", 1, 1, path)
            registry, manifest = self.inputs([record], ["dev"])
            with mock.patch.object(
                targeted_admission, "_sha256_file", side_effect=AssertionError("must not hash")
            ):
                with self.assertRaisesRegex(targeted_admission.AdmissionError, "positive integer"):
                    targeted_admission.finalize_admission(registry, manifest, max_files=0)
                with self.assertRaisesRegex(targeted_admission.AdmissionError, "must equal"):
                    targeted_admission.finalize_admission(registry, manifest, max_files=2)

    def test_manifest_claim_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claim.json"
            self.make_replay(path, episode_id=7, seed=70)
            record = self.record("A_ACCOUNT_ONLINE", 7, 70, path, claim="f" * 64)
            registry, manifest = self.inputs([record], ["dev"])
            with self.assertRaisesRegex(targeted_admission.AdmissionError, "claim mismatch"):
                targeted_admission.finalize_admission(registry, manifest, max_files=1)

    def test_same_episode_with_different_recomputed_sha_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left_path = root / "left.json"
            right_path = root / "right.json"
            self.make_replay(left_path, episode_id=99, seed=1, suffix="left")
            self.make_replay(right_path, episode_id=99, seed=2, suffix="right")
            left = self.record("A_ACCOUNT_ONLINE", 99, 1, left_path)
            right = self.record("B_OFFICIAL_DAILY", 99, 2, right_path)
            registry, manifest = self.inputs([left, right], ["dev", "frozen"])
            with self.assertRaisesRegex(targeted_admission.AdmissionError, "different replay SHA256"):
                targeted_admission.finalize_admission(registry, manifest, max_files=2)

    def test_global_seed_collision_fails_before_hashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left_path = root / "left.json"
            right_path = root / "right.json"
            left_path.write_text("not opened", encoding="utf-8")
            right_path.write_text("not opened", encoding="utf-8")
            left = self.record("A_ACCOUNT_ONLINE", 1, 777, left_path)
            right = self.record("B_OFFICIAL_DAILY", 2, 777, right_path)
            registry, manifest = self.inputs([left, right], ["dev", "frozen"])
            with mock.patch.object(
                targeted_admission, "_sha256_file", side_effect=AssertionError("must not hash")
            ):
                with self.assertRaisesRegex(targeted_admission.AdmissionError, "seed collision"):
                    targeted_admission.finalize_admission(registry, manifest, max_files=2)


if __name__ == "__main__":
    unittest.main()
