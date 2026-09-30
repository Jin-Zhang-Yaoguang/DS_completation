"""Trim a partially written PPO run back to its durable state marker."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def repair(root: Path) -> dict:
    state = json.loads((root / "ppo_state.json").read_text(encoding="utf-8"))
    completed = int(state["completed_iteration"])
    metrics_path = root / "ppo_metrics.jsonl"
    rows = [line for line in metrics_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    kept = []
    for line in rows:
        row = json.loads(line)
        if int(row.get("iteration", 0)) <= completed:
            kept.append(line)
    metrics_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    qualification = root / "snapshot_qualifications.jsonl"
    if qualification.exists():
        qrows = [line for line in qualification.read_text(encoding="utf-8").splitlines() if line.strip()]
        qkeep = [line for line in qrows if int(json.loads(line).get("iteration", 0)) <= completed]
        qualification.write_text("\n".join(qkeep) + ("\n" if qkeep else ""), encoding="utf-8")
    return {"root": str(root), "completed_iteration": completed, "metrics_kept": len(kept)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="+", type=Path)
    args = parser.parse_args()
    for root in args.roots:
        print(json.dumps(repair(root), ensure_ascii=False))
