#!/usr/bin/env python3
"""Stress one recent top fixed route against a heterogeneous live local pool."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
DATA = ROOT / "kaggle_Kaggriculture" / "model_data" / "kaggriculture_episodes_index" / "date=2026-08-25" / "data"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
POOL = (
    "v1_adaptive_market", "v2_survival_guard", "v5_rule_hybrid", "v8_kawa_lead2_slot",
    "v12a2_no_shop_gate", "v13c_a2_v8_no_wool_throttle", "v14_queue_best_response",
)


def load_cppsim():
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    return kagsim


KAGSIM = load_cppsim()


def play(stream: list[dict], live, seed: int, route_seat: int) -> tuple[float, float]:
    game = KAGSIM.Game(seed)
    while not game.done:
        step = game.step_count
        actions = [None, None]
        actions[route_seat] = stream[step]
        actions[1 - route_seat] = live(game.observe(1 - route_seat))
        game.step(actions[0], actions[1])
    return float(game.reward(0)), float(game.reward(1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", type=int, default=99630579)
    parser.add_argument("--team", default="tyz123456")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--output", default=str(Path(__file__).with_name("top_route_live_pool.json")))
    args = parser.parse_args()
    replay = json.loads((DATA / f"{args.episode}.json").read_text())
    source_seat = replay["info"]["TeamNames"].index(args.team)
    route = [pair[source_seat].get("action") or {} for pair in replay["steps"][1:720]]
    from kaggle_environments.agent import get_last_callable

    results = {}
    with TemporaryDirectory(prefix="v16_live_pool_") as directory:
        temp = Path(directory)
        for model_id in POOL:
            extract = temp / model_id
            extract.mkdir()
            with tarfile.open(MODEL / model_id / "submission.tar.gz", "r:gz") as tar:
                tar.extractall(extract, filter="data")
            live = get_last_callable((extract / "main.py").read_text(encoding="utf-8"), path=str(extract / "main.py"))
            rows = []
            for seed in range(args.seeds):
                for seat in (0, 1):
                    reward = play(route, live, seed, seat)
                    own, opp = reward[seat], reward[1 - seat]
                    rows.append((own, opp))
            results[model_id] = {
                "games": len(rows),
                "wins_ties_losses": [sum(a > b for a, b in rows), sum(a == b for a, b in rows), sum(a < b for a, b in rows)],
                "score_rate": statistics.mean(1.0 if a > b else 0.5 if a == b else 0.0 for a, b in rows),
                "mean_bank": statistics.mean(a for a, _ in rows),
                "mean_margin": statistics.mean(a - b for a, b in rows),
            }
            for name, module in list(sys.modules.items()):
                filename = getattr(module, "__file__", None)
                if filename and str(filename).startswith(str(extract)):
                    sys.modules.pop(name, None)
            while str(extract) in sys.path:
                sys.path.remove(str(extract))
    result = {
        "status": "FIXED_ROUTE_VS_LIVE_LOCAL_PROXY_NOT_GOLD_EVIDENCE",
        "route": {"team": args.team, "episode": args.episode, "source_seat": source_seat},
        "seeds": args.seeds,
        "pool": results,
        "family_equal_score_rate": statistics.mean(row["score_rate"] for row in results.values()),
        "worst_family_score_rate": min(row["score_rate"] for row in results.values()),
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
