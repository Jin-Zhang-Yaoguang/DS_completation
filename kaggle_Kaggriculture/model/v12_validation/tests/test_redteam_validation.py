"""Independent V12 validation red-team checks.

These tests never start a Kaggriculture environment.  They characterise the
sealed-panel contract, recompute all exposure exclusions, and verify that the
previous fingerprint/orientation bypasses remain closed.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import itertools
import json
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parents[1]
MODEL_ROOT = HERE.parent
PROJECT_ROOT = MODEL_ROOT.parents[1]
FROZEN = HERE / "frozen_v5"
V10 = MODEL_ROOT / "v10_replay_lolo_router"
V11 = MODEL_ROOT / "v11_iterative_league"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(V10))

from agent_factory import load_registry, registry_fingerprint  # noqa: E402
from pairwise_evaluate import (  # noqa: E402
    SCHEMA,
    evaluation_fingerprint,
    load_seed_manifest,
    stratified_seed_panel,
)
from kaggle_Kaggriculture.model.v12_validation.audit_results import (  # noqa: E402
    _candidate_report,
    audit,
)
from kaggle_Kaggriculture.model.v12_validation.protocol import (  # noqa: E402
    expected_tasks,
    target_pairs,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _all_numeric_seeds(path: Path) -> set[int]:
    seeds: set[int] = set()

    def visit(value) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "seed" and isinstance(child, (int, float)):
                    seeds.add(int(child))
                elif key == "seeds" and isinstance(child, list):
                    seeds.update(
                        int(item)
                        for item in child
                        if isinstance(item, (int, float))
                    )
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(_json(path))
    return seeds


class FrozenPanelRedTeamTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config_path = FROZEN / "validation_config.json"
        cls.config = _json(cls.config_path)
        cls.formal = _json(FROZEN / "formal_panel.json")

    def test_sha_manifest_and_serving_closure_are_current(self) -> None:
        declared = {}
        for line in (FROZEN / "validation_assets.sha256").read_text().splitlines():
            digest, name = line.split("  ", 1)
            declared[name] = digest
        self.assertEqual(
            declared,
            {
                name: _sha256(FROZEN / name)
                for name in (
                    "combined_registry.json",
                    "formal_panel.json",
                    "formal_seed_manifest.jsonl",
                    "submission_closure.json",
                    "validation_config.json",
                )
            },
        )
        registry = load_registry(FROZEN / "combined_registry.json")
        self.assertEqual(
            registry_fingerprint(registry),
            self.config["combined_registry_and_code_sha256"],
        )

    def test_external_parent_registry_provenance_is_current(self) -> None:
        """All non-candidate parents come from this registry and remain bound."""

        provenance = self.config["registry_provenance"]
        source = Path(provenance["source_registry"])
        self.assertEqual(_sha256(source), provenance["source_registry_file_sha256"])
        self.assertEqual(
            registry_fingerprint(load_registry(source)),
            provenance["source_registry_and_code_sha256"],
        )

    def test_locked_panel_excludes_every_declared_exposure(self) -> None:
        formal = {int(row["seed"]) for row in self.formal["records"]}
        self.assertEqual(len(formal), 100)
        self.assertEqual(self.formal["date_counts"], {
            "2026-08-18": 34,
            "2026-08-19": 33,
            "2026-08-20": 33,
        })
        self.assertTrue(
            all(
                row["split"] in {"train", "validation"}
                for row in self.formal["records"]
            )
        )
        exposed = set()
        for item in self.formal["exclusions"]["artifacts"]:
            path = Path(item["path"])
            if item["parser"] == "json_seed_keys_v1":
                exposed.update(_all_numeric_seeds(path))
            else:
                import re

                exposed.update(
                    int(value)
                    for value in re.findall(
                        r"(?i)\bseed\s*[`'\"]?([0-9]{8,12})[`'\"]?",
                        path.read_text(encoding="utf-8"),
                    )
                )
        self.assertFalse(exposed & formal)

    def test_run_contract_is_full_matrix_and_expected_fingerprint_is_recomputable(self) -> None:
        models = self.config["formal_models"]
        self.assertEqual(len(models), 10)
        pairs = target_pairs(self.config)
        self.assertEqual(len(pairs), 23)
        self.assertEqual(self.config["formal_protocol"]["expected_games"], 4_600)

        # Exactly the 23 unordered pairs consumed by the two direct-parent and
        # seven-common-opponent reports are frozen; no unused full matrix.
        strong = self.config["strong_opponents"]
        essential: set[frozenset[str]] = set()
        for item in self.config["candidates"]:
            candidate, parent = item["id"], item["parent"]
            essential.add(frozenset((candidate, parent)))
            essential.update(frozenset((candidate, opponent)) for opponent in strong)
            essential.update(
                frozenset((parent, opponent))
                for opponent in strong
                if opponent != parent
            )
        self.assertEqual(len(essential), 23)
        self.assertEqual({frozenset(pair) for pair in pairs}, essential)
        fingerprint, tasks, panel = expected_tasks(
            self.config, load_registry(FROZEN / "combined_registry.json")
        )
        self.assertEqual(len(fingerprint), 64)
        self.assertEqual(len(panel), 100)
        self.assertEqual(len(tasks), 4_600)


class StatisticRedTeamTest(unittest.TestCase):
    def test_common_opponent_uplift_is_same_source_and_source_clustered(self) -> None:
        sources = [
            ("2026-08-18", 1, "e1", "train"),
            ("2026-08-19", 2, "e2", "validation"),
        ]
        rows = defaultdict(list)

        def add(left: str, right: str, source, left_scores) -> None:
            key = (frozenset((left, right)), source)
            for seat, score in enumerate(left_scores):
                rows[key].append(
                    {
                        "model_a": left,
                        "model_b": right,
                        "model_a_seat": seat,
                        "score_a": score,
                        "margin_a": (score - 0.5) * 100.0,
                    }
                )

        for source in sources:
            add("candidate", "parent", source, (0.5, 0.5))
            add("candidate", "opponent", source, (1.0, 0.5))
            add("parent", "opponent", source, (0.5, 0.0))
        report = _candidate_report(
            "candidate",
            "parent",
            ["parent", "opponent"],
            sources,
            rows,
            {
                "direct_parent_score_point_min": 0.5,
                "direct_parent_score_ci95_low_min": 0.5,
                "common_opponent_uplift_point_min": 0.0,
                "common_opponent_uplift_ci95_low_min": 0.0,
                "worst_common_opponent_point_min": -0.02,
            },
        )
        self.assertEqual(report["direct_parent"]["paired_sources"], 2)
        self.assertEqual(
            report["common_opponent_uplift"]["paired_source_clusters"], 2
        )
        self.assertAlmostEqual(
            report["common_opponent_uplift"]["score_uplift"], 0.5
        )

    def test_auditor_rejects_unbound_run_fingerprint(self) -> None:
        """Every row is otherwise well formed, but its fingerprint is forged."""

        config_path = FROZEN / "validation_config.json"
        config = _json(config_path)
        _, tasks, _ = expected_tasks(
            config, load_registry(FROZEN / "combined_registry.json")
        )
        with tempfile.TemporaryDirectory(prefix="v12-redteam-") as directory:
            games = Path(directory) / "forged.jsonl"
            with games.open("w", encoding="utf-8") as handle:
                for task in tasks:
                    seat = int(task["model_a_seat"])
                    left, right = task["model_a"], task["model_b"]
                    handle.write(
                        json.dumps(
                            {
                                "schema": SCHEMA,
                                **task,
                                "run_fingerprint": "arbitrary-unbound-value",
                                "seat_models": [left, right]
                                if seat == 0
                                else [right, left],
                                "closed_loop": True,
                                "trace_agent": False,
                                "engine": "kaggle_environments.make(kaggriculture)",
                                "statuses": ["DONE", "DONE"],
                                "rewards": [100.0, 100.0],
                                "done": True,
                                "reward_a": 100.0,
                                "reward_b": 100.0,
                                "margin_a": 0.0,
                                "score_a": 0.5,
                                "error": None,
                            },
                            separators=(",", ":"),
                        )
                        + "\n"
                    )
            report = audit(config_path, games)
            self.assertFalse(report["integrity_passed"])
            self.assertFalse(report["checks"]["exact_run_fingerprint"])
            self.assertFalse(report["checks"]["zero_row_errors"])


if __name__ == "__main__":
    unittest.main()
