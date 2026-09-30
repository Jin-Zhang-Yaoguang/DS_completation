"""Build a 72-task alignment from exposed, immutable result artifacts."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
INPUTS = {
    "baseline": BASE / "oracle/a2_parent_baseline_games.jsonl",
    "oracle": BASE / "oracle/a2_parent_oracle_games.jsonl",
    "stateful": BASE / "dev_runs/queue_solver_stateful_screen36/games.jsonl",
    "ablation": HERE / "public_equality_ablation.json",
}
OUT = HERE / "task_alignment.json"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _key(row: Mapping[str, Any], seat_field: str) -> tuple[int, int]:
    return int(row["source"]["seed"]), int(row[seat_field])


def _stateful_outcome(row: Mapping[str, Any]) -> str:
    score = float(row["score_a"])
    return "W" if score == 1.0 else "T" if score == 0.5 else "L"


def main() -> None:
    baseline = {_key(row, "candidate_seat"): row for row in _jsonl(INPUTS["baseline"])}
    oracle = {_key(row, "candidate_seat"): row for row in _jsonl(INPUTS["oracle"])}
    stateful = {_key(row, "model_a_seat"): row for row in _jsonl(INPUTS["stateful"])}
    ablation_payload = json.loads(INPUTS["ablation"].read_text(encoding="utf-8"))
    ablation = {_key(row, "candidate_seat"): row for row in ablation_payload["rows"]}
    if not (set(baseline) == set(oracle) == set(stateful) == set(ablation)) or len(baseline) != 72:
        raise AssertionError("task keys do not form the same exposed 72-game panel")

    rows = []
    for key in sorted(baseline):
        b, o, s, a = baseline[key], oracle[key], stateful[key], ablation[key]
        status = s["agent_diagnostics"]["v14_queue_best_response"]["underlying"]
        so = _stateful_outcome(s)
        rows.append({
            "source": dict(b["source"]),
            "candidate_seat": key[1],
            "branch_pair": f"{o.get('candidate_branch')}/{o.get('opponent_branch')}",
            "baseline": {"outcome": b["outcome"], "margin": float(b["margin"])},
            "oracle": {
                "outcome": o["outcome"],
                "margin": float(o["margin"]),
                "eligible_steps": int(o["eligible_steps"]),
                "triggered_steps": int(o["triggered_steps"]),
                "first_trigger_step": int(o["events"][0]["step"]) if o["events"] else None,
            },
            "stateful": {
                "outcome": so,
                "margin": float(s["margin_a"]),
                "reordered_steps": int(status["reordered_steps"]),
                "shadow_trusted": bool(status["shadow_trusted"]),
                "shadow_faults": int(status["shadow_faults"]),
                "skip_reasons": dict(status["skip_reasons"]),
            },
            "public_equality_ablation": {
                "outcome": a["outcome"],
                "margin": float(a["margin"]),
                "reordered_steps": int(a["reordered_steps"]),
                "shadow_trusted": bool(a["shadow_trusted"]),
                "shadow_faults": int(a["shadow_faults"]),
            },
            "transition": f"{b['outcome']}->{o['outcome']}/{so}->{a['outcome']}",
            "oracle_stateful_outcome_equal": o["outcome"] == so,
            "oracle_ablation_outcome_equal": o["outcome"] == a["outcome"],
            "oracle_ablation_rewards_equal": a["rewards"] == [float(value) for value in o["rewards"]],
        })

    payload = {
        "schema": "kaggriculture-v14-oracle-stateful-task-alignment-1",
        "epistemic_status": "alignment of already-exposed V13 screen36 artifacts; not validation",
        "scope": {
            "v14_fresh_screen_read": False,
            "v14_confirm_read": False,
            "test_read": False,
        },
        "input_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in INPUTS.items()
        },
        "games": len(rows),
        "oracle_to_stateful": dict(sorted(Counter(
            f"{row['oracle']['outcome']}->{row['stateful']['outcome']}" for row in rows
        ).items())),
        "oracle_to_public_equality_ablation": dict(sorted(Counter(
            f"{row['oracle']['outcome']}->{row['public_equality_ablation']['outcome']}" for row in rows
        ).items())),
        "stateful_reordered_steps": sum(row["stateful"]["reordered_steps"] for row in rows),
        "ablation_reordered_steps": sum(row["public_equality_ablation"]["reordered_steps"] for row in rows),
        "rows": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "games", "oracle_to_stateful", "oracle_to_public_equality_ablation",
        "stateful_reordered_steps", "ablation_reordered_steps",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
