#!/usr/bin/env python3
"""Evaluate a recent tyz route through A2's live repair executor."""

from __future__ import annotations

import argparse
import importlib.util
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
POOL = ("v1_adaptive_market", "v2_survival_guard", "v5_rule_hybrid", "v8_kawa_lead2_slot",
        "v12a2_no_shop_gate", "v13c_a2_v8_no_wool_throttle", "v14_queue_best_response")


def load_cppsim():
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    return kagsim


KAGSIM = load_cppsim()


def load_a2():
    path = MODEL / "v1_adaptive_market" / "main.py"
    spec = importlib.util.spec_from_file_location("v17_tyz_adaptive_base", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def play(candidate, opponent, seed: int, candidate_seat: int) -> tuple[float, float]:
    game = KAGSIM.Game(seed)
    while not game.done:
        actions = [None, None]
        actions[candidate_seat] = candidate(game.observe(candidate_seat))
        actions[1 - candidate_seat] = opponent(game.observe(1 - candidate_seat))
        game.step(actions[0], actions[1])
    return float(game.reward(0)), float(game.reward(1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", type=int, default=99630579)
    parser.add_argument("--team", default="tyz123456")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--output", default=str(Path(__file__).with_name("tyz_adaptive_live_pool.json")))
    args = parser.parse_args()
    replay = json.loads((DATA / f"{args.episode}.json").read_text())
    seat = replay["info"]["TeamNames"].index(args.team)
    route = [pair[seat].get("action") or {} for pair in replay["steps"][1:720]]
    base = load_a2()

    def candidate(obs):
        base._ACTIONS = route
        return base._CORE_AGENT(obs)

    from kaggle_environments.agent import get_last_callable
    results = {}
    with TemporaryDirectory(prefix="v17_tyz_live_pool_") as directory:
        temp = Path(directory)
        for model_id in POOL:
            extract = temp / model_id
            extract.mkdir()
            with tarfile.open(MODEL / model_id / "submission.tar.gz", "r:gz") as tar:
                tar.extractall(extract, filter="data")
            opponent = get_last_callable((extract / "main.py").read_text(encoding="utf-8"), path=str(extract / "main.py"))
            rows = []
            for seed_value in range(args.seeds):
                for candidate_seat in (0, 1):
                    reward = play(candidate, opponent, seed_value, candidate_seat)
                    rows.append((reward[candidate_seat], reward[1 - candidate_seat]))
            results[model_id] = {
                "games": len(rows), "wins_ties_losses": [sum(a > b for a, b in rows), sum(a == b for a, b in rows), sum(a < b for a, b in rows)],
                "score_rate": statistics.mean(1.0 if a > b else 0.5 if a == b else 0.0 for a, b in rows),
                "mean_bank": statistics.mean(a for a, _ in rows), "mean_margin": statistics.mean(a - b for a, b in rows),
            }
            for name, module in list(sys.modules.items()):
                filename = getattr(module, "__file__", None)
                if filename and str(filename).startswith(str(extract)):
                    sys.modules.pop(name, None)
            while str(extract) in sys.path:
                sys.path.remove(str(extract))
    result = {
        "status": "PUBLIC_ROUTE_DERIVED_LIVE_REPAIR_DEVELOPMENT",
        "route": {"team": args.team, "episode": args.episode}, "seeds": args.seeds, "pool": results,
        "family_equal_score_rate": statistics.mean(row["score_rate"] for row in results.values()),
        "worst_family_score_rate": min(row["score_rate"] for row in results.values()),
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
