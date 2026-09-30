#!/usr/bin/env python3
"""Independently recompute V118 gold gate and validate all locked inputs."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
V118 = HERE.parent
MODEL = V118.parent
PROJECT = MODEL.parent
BASE = PROJECT / "model_data/round_robin/gold18_replay_admitted_128x2_20260830"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name: str, passed: bool, detail=None) -> dict:
    return {"name": name, "passed": bool(passed), "detail": detail}


def main() -> int:
    run = json.loads((HERE / "run_manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
    admission = json.loads((HERE / "admission_audit.json").read_text(encoding="utf-8"))
    preflight = json.loads((HERE / "preflight_results.json").read_text(encoding="utf-8"))
    account = json.loads((HERE / "account_panel.json").read_text(encoding="utf-8"))["final_test"]
    official = json.loads((BASE / "official_panel.json").read_text(encoding="utf-8"))["final_test"]
    rows = [json.loads(line) for line in (HERE / "games.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    checks: list[dict] = []

    checks.append(check("admission_pass", admission["status"] == "PASS" and all(admission["checks"].values()), admission["checks"]))
    checks.append(check("preflight_pass", preflight["status"] == "PASS" and all(preflight["checks"].values()), preflight["checks"]))
    checks.append(check("candidate_hash_exact", sha256(PROJECT / run["candidate"]["path"]) == run["candidate"]["sha256"]))
    input_hash_errors = []
    for model, spec in run["opponents"].items():
        if sha256(PROJECT / spec["path"]) != spec["sha256"]:
            input_hash_errors.append(model)
    for panel, spec in run["panels"].items():
        if sha256(PROJECT / spec["path"]) != spec["sha256"]:
            input_hash_errors.append(panel)
    checks.append(check("all_locked_input_hashes_exact", not input_hash_errors, input_hash_errors))

    checks.append(check("game_count_9216", len(rows) == 9216, len(rows)))
    checks.append(check("zero_errors", all(row["status"] == "DONE" for row in rows), Counter(row["status"] for row in rows)))
    keys = {(row["panel"], row["opponent"], row["candidate_seat"], row["source_id"]) for row in rows}
    checks.append(check("task_keys_unique", len(keys) == len(rows), len(keys)))
    checks.append(check("all_719_calls", all(row["calls"] == 719 for row in rows)))
    checks.append(check("margin_identity", all(row["candidate_reward"] - row["opponent_reward"] == row["candidate_margin"] for row in rows)))

    panel_ids = {
        "account_online": {str(row["episode_id"]) for row in account},
        "official_daily": {str(row["episode_id"]) for row in official},
    }
    used_ids = {
        panel: {str(row["source_id"]) for row in rows if row["panel"] == panel}
        for panel in panel_ids
    }
    checks.append(check("only_frozen_panel_ids_used", used_ids == panel_ids, {k: len(v) for k, v in used_ids.items()}))
    pair_counts = Counter((row["panel"], row["opponent"]) for row in rows)
    checks.append(check("each_panel_opponent_has_256_games", len(pair_counts) == 36 and set(pair_counts.values()) == {256}, Counter(pair_counts.values())))
    seat_counts = Counter((row["panel"], row["opponent"], row["candidate_seat"]) for row in rows)
    checks.append(check("each_seat_direction_has_128_games", len(seat_counts) == 72 and set(seat_counts.values()) == {128}, Counter(seat_counts.values())))

    recomputed = {}
    per_opponent = defaultdict(Counter)
    for panel in panel_ids:
        values = [row for row in rows if row["panel"] == panel]
        wins = sum(row["candidate_margin"] > 0 for row in values)
        ties = sum(row["candidate_margin"] == 0 for row in values)
        losses = sum(row["candidate_margin"] < 0 for row in values)
        recomputed[panel] = {
            "games": len(values), "wins": wins, "ties": ties, "losses": losses,
            "pure_win_rate": wins / len(values),
        }
        for row in values:
            result = "wins" if row["candidate_margin"] > 0 else "ties" if row["candidate_margin"] == 0 else "losses"
            per_opponent[(panel, row["opponent"])][result] += 1
            per_opponent[(panel, row["opponent"])]["games"] += 1
    aggregate_errors = []
    for panel, values in recomputed.items():
        saved = summary["panels"][panel]
        for field in ("games", "wins", "ties", "losses", "pure_win_rate"):
            if saved[field] != values[field]:
                aggregate_errors.append({"panel": panel, "field": field, "saved": saved[field], "recomputed": values[field]})
        for row in saved["by_opponent"]:
            got = per_opponent[(panel, row["opponent"])]
            for field in ("games", "wins", "ties", "losses"):
                if row[field] != got[field]:
                    aggregate_errors.append({"panel": panel, "opponent": row["opponent"], "field": field})
    checks.append(check("aggregates_recompute_exactly", not aggregate_errors, aggregate_errors[:20]))
    checks.append(check(
        "strict_gold_gate_recomputed",
        recomputed["account_online"]["pure_win_rate"] >= 0.75
        and recomputed["official_daily"]["pure_win_rate"] >= 0.75
        and summary["gold_gate"]["pass"] is True,
        recomputed,
    ))
    checks.append(check(
        "account_official_isolation",
        not ({row["episode_id"] for row in account} & {row["episode_id"] for row in official})
        and not ({row["seed"] for row in account} & {row["seed"] for row in official})
        and not ({row["scenario_sha256"] for row in account} & {row["scenario_sha256"] for row in official}),
    ))
    result = {
        "schema": "kaggriculture-v118-gold-registration-validation-v1",
        "checks": checks,
        "passed": sum(row["passed"] for row in checks),
        "failed": sum(not row["passed"] for row in checks),
        "recomputed": recomputed,
        "status": "PASS" if all(row["passed"] for row in checks) else "FAIL",
    }
    (HERE / "validation_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
