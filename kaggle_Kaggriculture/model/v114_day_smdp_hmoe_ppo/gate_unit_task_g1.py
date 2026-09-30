"""Apply the preregistered V12 G1 unit-skill gate to heldout rollouts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluation = json.loads(args.evaluation.read_text(encoding="utf-8"))
    rows = evaluation.get("rows") or []
    if not rows:
        raise ValueError("evaluation has no rows")
    per_game = []
    for row in rows:
        audit = row["audit"]["unit"]
        completed = int(audit["completed_tasks"])
        failed = int(audit["failed_tasks"]) + int(audit["timed_out_tasks"])
        denominator = completed + failed
        per_game.append({
            "seed": row["seed"], "seat": row["seat"],
            "completion_rate": completed / denominator if denominator else 0.0,
            "completed": completed, "failed_or_timeout": failed,
            "blocked_turns": int(audit["blocked_turns"]),
            "unit_market_actions": int(audit["market_actions"]),
            "stale_contracts_caught_before_emit": int(audit["failed_tasks"]),
        })
    completion = [row["completion_rate"] for row in per_game]
    ordered = sorted(completion)
    p10 = ordered[int(0.1 * (len(ordered) - 1))]
    total_steps = sum(int(row["audit"]["action_steps"]) for row in rows)
    blocked = sum(row["blocked_turns"] for row in per_game)
    blocked_rate = blocked / max(1, total_steps)
    emitted_illegal_actions = 0 if all(row.get("error") is None for row in rows) else 1
    market_actions = sum(row["unit_market_actions"] for row in per_game)
    passed = (
        sum(completion) / len(completion) >= 0.95
        and p10 >= 0.90
        and emitted_illegal_actions == 0
        and blocked_rate <= 0.01
        and market_actions == 0
    )
    report = {
        "schema": "kaggriculture-v114-v12-unit-skill-g1-v1",
        "status": (
            "PASS_G1_UNIT_SKILL_ONLY_NOT_G2_NOT_FOUNDATION_NOT_GOLD"
            if passed else "FAIL_G1_UNIT_SKILL"
        ),
        "passed": passed,
        "checkpoint": str(args.checkpoint.resolve()),
        "checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        "training_method": "candidate_level_duration_aware_smdp_ppo_v1",
        "evaluation": str(args.evaluation.resolve()),
        "evaluation_sha256": hashlib.sha256(args.evaluation.read_bytes()).hexdigest(),
        "heldout_from_ppo_smoke_seed": True,
        "fresh_l0_l1_evidence": False,
        "games": len(rows),
        "mean_task_completion_rate": sum(completion) / len(completion),
        "p10_task_completion_rate": p10,
        "emitted_illegal_actions": emitted_illegal_actions,
        "stale_contracts_caught_before_emit": sum(row["stale_contracts_caught_before_emit"] for row in per_game),
        "continuous_block_rate": blocked_rate,
        "unit_market_actions": market_actions,
        "thresholds": {
            "mean_task_completion_rate_min": 0.95,
            "p10_task_completion_rate_min": 0.90,
            "emitted_illegal_actions": 0,
            "continuous_block_rate_max": 0.01,
            "unit_market_actions": 0,
        },
        "per_game": per_game,
        "qualification_boundary": "unit skill only; no claim about economy, G2, L0, L1 or gold",
    }
    atomic_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
