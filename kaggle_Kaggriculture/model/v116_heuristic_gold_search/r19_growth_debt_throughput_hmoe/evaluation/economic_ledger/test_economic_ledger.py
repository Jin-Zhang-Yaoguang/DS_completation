#!/usr/bin/env python3
"""Integrity tests for the persisted R17/R18/R19 economic ledger."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
EXPECTED_ENGINE_SHA = "cfc6708a693b04cd34fcb3b8d60c90d54c5c6b8d64bc6b9be1eb900ad5dd8ba2"
EXPECTED_CANDIDATES = {
    "R17": "7d6504512aac7bb39fdf49718022e3ae6c61353ffe0589efd3ce2fd5e333d908",
    "R18": "55fa7ba1aa6f8791cf208441b3d9ed740e6f99e48038dd3c71580d2e93bf2511",
    "R19": "45e48f244123334329e9f35dd01d461ffc2919eac0ffaff4ce7d471cdb802ed7",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class EconomicLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = [
            json.loads(line)
            for line in (HERE / "games.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cls.summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((HERE / "run_manifest.json").read_text(encoding="utf-8"))

    def test_exact_six_game_panel(self) -> None:
        self.assertEqual(len(self.rows), 6)
        self.assertEqual(
            {(row["version"], row["candidate_seat"]) for row in self.rows},
            {(version, seat) for version in EXPECTED_CANDIDATES for seat in (0, 1)},
        )
        self.assertTrue(all(row["seed"] == 7100 for row in self.rows))
        self.assertTrue(all(row["opponent"] == "idle" for row in self.rows))

    def test_candidate_never_receives_accounting(self) -> None:
        self.assertTrue(all(row["observation_boundary_clean"] for row in self.rows))
        self.assertTrue(all(row["checks"]["observation_has_no_accounting"] for row in self.rows))
        self.assertEqual(self.manifest["candidate_truth_visibility"], "NONE")
        self.assertEqual(
            self.manifest["truth_read_order"],
            "candidate_action_first_then_evaluator_accounting",
        )
        for version, expected in EXPECTED_CANDIDATES.items():
            evidence = self.manifest["candidates"][version]
            self.assertEqual(evidence["sha256"], expected)
            self.assertTrue(evidence["boundary_static_ok"])
            self.assertEqual(evidence["forbidden_accounting_tokens"], [])

    def test_engine_and_artifact_hashes(self) -> None:
        engine = self.manifest["accounting_engine"]
        self.assertEqual(engine["module_sha256"], EXPECTED_ENGINE_SHA)
        self.assertEqual(engine["verification_status"], "PASS_ACCOUNTING_ENGINE")
        self.assertGreaterEqual(engine["verification_tests"], 6)
        self.assertEqual(self.manifest["games_sha256"], sha256(HERE / "games.jsonl"))
        self.assertEqual(self.manifest["summary_sha256"], sha256(HERE / "summary.json"))

    def test_every_game_is_complete_and_conserves(self) -> None:
        for row in self.rows:
            self.assertEqual(row["status"], "DONE")
            self.assertEqual(row["calls"], 719)
            self.assertEqual(row["schema_issues"], [])
            self.assertTrue(all(row["checks"].values()))
            self.assertTrue(all(value == 0 for value in row["item_conservation_residuals"].values()))
            self.assertTrue(all(value == 0 for value in row["seed_conservation_residuals"].values()))
            self.assertEqual(row["cash_conservation_residual"], 0.0)
            self.assertEqual(len(row["daily_assets"]), 30)

    def test_summary_matches_rows_and_is_diagnostic_only(self) -> None:
        self.assertTrue(self.summary["all_games_clean"])
        self.assertEqual(set(self.summary["by_version"]), set(EXPECTED_CANDIDATES))
        self.assertFalse(self.summary["scope"]["p2"])
        self.assertFalse(self.summary["scope"]["replay"])
        self.assertFalse(self.summary["scope"]["gold_evidence"])
        for version in EXPECTED_CANDIDATES:
            rows = [row for row in self.rows if row["version"] == version]
            expected_bank = sum(float(row["bank"]) for row in rows) / len(rows)
            self.assertEqual(self.summary["by_version"][version]["bank_mean"], expected_bank)


if __name__ == "__main__":
    unittest.main(verbosity=2)
