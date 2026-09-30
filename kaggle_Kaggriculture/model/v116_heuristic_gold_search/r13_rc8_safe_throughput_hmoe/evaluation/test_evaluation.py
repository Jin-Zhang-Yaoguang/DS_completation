#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("r13_evaluate_test", HERE / "evaluate.py")
assert SPEC and SPEC.loader
evaluate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluate)


def done_row(
    mode: str,
    opponent: str,
    seed: int,
    seat: int,
    *,
    win: bool = True,
    own_bank: float = 120_000.0,
    assets: int = 60,
) -> dict:
    rival_bank = own_bank - 10_000.0 if win else own_bank + 10_000.0
    margin = own_bank - rival_bank
    return {
        "schema": "synthetic",
        "task_id": f"x__{mode}__{opponent}__{seed}__s{seat}",
        "panel": "synthetic",
        "status": "DONE",
        "error": None,
        "calls": 719,
        "mode": mode,
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "win": int(win),
        "tie": 0,
        "loss": int(not win),
        "score": float(win),
        "own_bank": own_bank,
        "opponent_bank": rival_bank,
        "margin": margin,
        "candidate_schema_violations": 0,
        "opponent_schema_violations": 0,
        "terminal": {"production_assets": assets},
    }


class EvaluationTest(unittest.TestCase):
    def test_exact_panel_sizes_modes_and_pairing(self) -> None:
        candidate = HERE.parent / "main.py"
        p2 = evaluate.build_tasks("p2", candidate)
        p3 = evaluate.build_tasks("p3", candidate)
        self.assertEqual(72, len(p2))
        self.assertEqual(432, len(p3))
        self.assertEqual(6, len(evaluate.MODES))
        self.assertEqual(5, len(evaluate.FIXED_MODES))
        self.assertEqual({0, 1}, {row["candidate_seat"] for row in p3})
        self.assertEqual(set(evaluate.MODES), {row["mode"] for row in p3})
        self.assertEqual(set(evaluate.GOLD_POOL), {row["opponent"] for row in p3})
        self.assertEqual(set(evaluate.P2_SEEDS), {row["seed"] for row in p2})
        self.assertEqual(set(evaluate.P3_SEEDS), {row["seed"] for row in p3})

    def test_action_validator(self) -> None:
        observation = {"player": 0, "farms": [{"hands": [[1, 1]]}, {"hands": []}]}
        valid = {
            "farmer": ["PASS"],
            "hands": [["PLANT", "WHEAT"]],
            "market": [["BUY_SEED", "WHEAT", 2]],
        }
        self.assertEqual([], evaluate.validate_action(valid, observation))
        invalid = {
            "farmer": ["PASS", 1],
            "hands": [],
            "market": [["SELL", "WHEAT", 0]],
        }
        self.assertGreaterEqual(len(evaluate.validate_action(invalid, observation)), 3)

    def test_p2_thresholds_and_errors_are_nonwins(self) -> None:
        rows = [
            done_row(mode, "idle", seed, seat)
            for mode in evaluate.MODES
            for seed in evaluate.P2_SEEDS
            for seat in (0, 1)
        ]
        summary = evaluate.summarize(rows, "p2")
        self.assertTrue(evaluate.decide(summary)["passed"])
        rows[0] = evaluate.error_row({
            "task_id": "x",
            "panel": "p2",
            "mode": "router",
            "opponent": "idle",
            "seed": 7100,
            "candidate_seat": 0,
        }, "synthetic")
        failed = evaluate.summarize(rows, "p2")
        self.assertFalse(evaluate.decide(failed)["passed"])
        self.assertEqual(1, failed["overall"]["errors_as_nonwins"])
        self.assertEqual(11 / 12, failed["by_mode"]["router"]["pure_win_rate"])

    def test_p2_each_fixed_and_global_asset_gate(self) -> None:
        rows = [
            done_row(mode, "idle", seed, seat)
            for mode in evaluate.MODES
            for seed in evaluate.P2_SEEDS
            for seat in (0, 1)
        ]
        target = next(row for row in rows if row["mode"] == "fixed_wool")
        target["own_bank"] = -300_000.0
        target["margin"] = -310_000.0
        target["win"], target["loss"] = 0, 1
        target["terminal"]["production_assets"] = 57
        decision = evaluate.decide(evaluate.summarize(rows, "p2"))
        self.assertFalse(decision["passed"])
        self.assertIn("fixed_wool_mean_bank_below_90000", decision["failures"])
        self.assertIn("minimum_terminal_production_assets_below_58", decision["failures"])

    def test_p3_all_special_gates(self) -> None:
        matchup_keys = [
            (opponent, seed, seat)
            for opponent in evaluate.GOLD_POOL
            for seed in evaluate.P3_SEEDS
            for seat in (0, 1)
        ]
        fixed_ranges = {
            evaluate.FIXED_MODES[0]: range(0, 26),
            evaluate.FIXED_MODES[1]: range(20, 36),
            evaluate.FIXED_MODES[2]: range(34, 46),
            evaluate.FIXED_MODES[3]: range(44, 56),
            evaluate.FIXED_MODES[4]: range(54, 60),
        }
        rows = []
        for mode in evaluate.MODES:
            won = set(range(54)) if mode == "router" else set(fixed_ranges[mode])
            for index, (opponent, seed, seat) in enumerate(matchup_keys):
                is_win = index in won
                rows.append(done_row(
                    mode, opponent, seed, seat,
                    win=is_win,
                    own_bank=120_000.0 if is_win else 100_000.0,
                ))
        summary = evaluate.summarize(rows, "p3")
        special = summary["p3_special"]
        self.assertEqual(72, special["matchups"])
        self.assertTrue(all(value >= 2 for value in special["fixed_exclusive_wins"].values()))
        self.assertGreaterEqual(special["fixed_outcome_oracle_pure_win_rate"], 0.80)
        self.assertGreaterEqual(special["router_positive_opponent_medians"], 12)
        self.assertGreaterEqual(special["router_positive_flips_vs_best_fixed"], 1)
        self.assertTrue(evaluate.decide(summary)["passed"])

    def test_preflight_manifest_hashes_and_worker_limit(self) -> None:
        candidate = HERE.parent / "main.py"
        with self.assertRaises(ValueError):
            evaluate.preflight("p2", candidate, 9)
        tasks, manifest = evaluate.preflight("p2", candidate, 1)
        self.assertEqual(72, len(tasks))
        self.assertEqual(72, manifest["planned_games"])
        self.assertEqual(list(evaluate.MODES), manifest["candidate"]["declared_modes"])
        self.assertEqual(64, len(manifest["candidate"]["entrypoint_sha256"]))
        self.assertEqual(64, len(manifest["candidate"]["python_tree_sha256"]))
        self.assertEqual(64, len(manifest["engine"]["binary_sha256"]))
        self.assertEqual(64, len(manifest["agent_factory"]["python_tree_sha256"]))
        self.assertEqual(64, len(manifest["task_plan_sha256"]))
        self.assertEqual(
            {"evaluate.py", "test_evaluation.py", "README.md"},
            set(manifest["evaluation_source_hashes"]),
        )

    def test_refuses_overwrite_before_preflight_or_games(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            existing = Path(raw) / "existing"
            existing.mkdir()
            with self.assertRaises(FileExistsError):
                evaluate.run("p2", HERE.parent / "main.py", existing, 1)


if __name__ == "__main__":
    unittest.main()
