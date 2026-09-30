#!/usr/bin/env python3
"""Paired closed-loop check against later packaged local strategy proxies."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
LATE_POOL = (
    "v12a2_no_shop_gate",
    "v13c_a2_v8_no_wool_throttle",
    "v14_queue_best_response",
)

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from contextual_full_template_a2s2 import make_agent  # noqa: E402
from run_contextual_full_template_a2s2 import (  # noqa: E402
    cluster_ci,
    load_a2,
    pair_summary,
    play_live,
    score,
)


def cleanup_modules(directory: Path) -> None:
    for name, module in list(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if filename and str(filename).startswith(str(directory)):
            sys.modules.pop(name, None)
    while str(directory) in sys.path:
        sys.path.remove(str(directory))


def load_submission(model_id: str, branch: str, root: Path) -> tuple[Callable, Path]:
    from kaggle_environments.agent import get_last_callable

    extract = root / f"{model_id}_{branch}"
    extract.mkdir()
    with tarfile.open(MODEL / model_id / "submission.tar.gz", "r:gz") as archive:
        archive.extractall(extract, filter="data")
    entry = extract / "main.py"
    live = get_last_callable(entry.read_text(encoding="utf-8"), path=str(entry))
    return live, extract


def run_branch(model_id: str, branch: str, seed_count: int, root: Path) -> dict[tuple[int, int], tuple[float, float, dict[str, Any] | None]]:
    opponent, extract = load_submission(model_id, branch, root)
    result = {}
    if branch == "baseline":
        own = load_a2(f"late_{model_id}").agent
        routed = None
    else:
        routed = make_agent()
        own = routed
    try:
        for seed in range(seed_count):
            for own_seat in (0, 1):
                rewards = play_live(seed, own, opponent) if own_seat == 0 else play_live(seed, opponent, own)
                diag = None if routed is None else routed.diagnostics(own_seat)
                result[(seed, own_seat)] = (float(rewards[own_seat]), float(rewards[1 - own_seat]), diag)
    finally:
        cleanup_modules(extract)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=24)
    parser.add_argument("--output", default=str(HERE / "contextual_full_template_a2s2_late_proxy_results.json"))
    args = parser.parse_args()
    rows = []
    with TemporaryDirectory(prefix="v16_a2s2_late_proxy_") as directory:
        temp = Path(directory)
        for model_id in LATE_POOL:
            baseline = run_branch(model_id, "baseline", args.seeds, temp)
            candidate = run_branch(model_id, "candidate", args.seeds, temp)
            if set(baseline) != set(candidate):
                raise AssertionError("paired seed/seat sets differ")
            for seed, own_seat in sorted(baseline):
                base_own, base_opp, _ = baseline[(seed, own_seat)]
                cand_own, cand_opp, diag = candidate[(seed, own_seat)]
                assert diag is not None
                rows.append({
                    "opponent": model_id,
                    "seed": seed,
                    "cluster": f"{model_id}:{seed}",
                    "own_seat": own_seat,
                    "baseline_own": base_own,
                    "baseline_opponent": base_opp,
                    "candidate_own": cand_own,
                    "candidate_opponent": cand_opp,
                    "baseline_margin": base_own - base_opp,
                    "candidate_margin": cand_own - cand_opp,
                    "baseline_score": score(base_own, base_opp),
                    "candidate_score": score(cand_own, cand_opp),
                    "selected": diag["selected"],
                    "prefix_complete": diag["prefix_complete"],
                    "prefix_match": diag["prefix_match"],
                })
    by_opponent = {model_id: pair_summary([row for row in rows if row["opponent"] == model_id]) for model_id in LATE_POOL}
    overall = pair_summary(rows)
    overall.update(cluster_ci(rows, "cluster"))
    overall["family_equal_baseline_score_rate"] = statistics.mean(row["baseline_score_rate"] for row in by_opponent.values())
    overall["family_equal_candidate_score_rate"] = statistics.mean(row["candidate_score_rate"] for row in by_opponent.values())
    overall["worst_family_candidate_score_rate"] = min(row["candidate_score_rate"] for row in by_opponent.values())
    overall["prefix_failures"] = sum(not row["prefix_complete"] or not row["prefix_match"] for row in rows)
    overall["selection_counts"] = {name: sum(row["selected"] == name for row in rows) for name in sorted({row["selected"] for row in rows})}
    result = {
        "status": "CLOSED_LOOP_LATER_LOCAL_PROXY_DEVELOPMENT_NOT_GOLD_EVIDENCE",
        "engine": "cppsim 1.32.7",
        "seeds": args.seeds,
        "command": ".venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/run_contextual_late_proxy_a2s2.py --seeds 24",
        "overall": overall,
        "by_opponent": by_opponent,
        "rows": rows,
        "failure_boundaries": [
            "packaged local strategies are closed-loop but remain internal historical proxies",
            "they do not substitute for current top-team packages or future-date confirmation",
            "A2 is only the paired regression anchor",
        ],
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "overall": overall, "by_opponent": by_opponent, "output": args.output}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

