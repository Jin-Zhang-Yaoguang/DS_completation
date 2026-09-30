#!/usr/bin/env python3
"""Screen Top5 teacher trajectories as complete route experts against V76/V20."""

from __future__ import annotations

import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
FACTORY = MODEL / "v10_replay_lolo_router"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore  # noqa: E402
from agent_factory import Registry, create_agent  # type: ignore  # noqa: E402


BASE = MODEL / "v119_center_livestock_spatial_moe/main.py"
OPPONENTS = {
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
    "v20": MODEL / "v20_demand_timing_moe/main.py",
}
SEEDS = (41490561, 75271437, 109028483, 163550927, 228491743, 291770611, 337401829, 398112271)


def load(path: Path, model_id: str):
    registry = Registry(path=HERE / "route_screen_registry.json", models={}, raw={})
    return create_agent(registry, {"id": model_id, "kind": "python", "path": str(path), "entrypoint": "agent"})


def routes() -> list[dict]:
    receipt = json.loads((HERE / "replay_data/download_receipt.json").read_text(encoding="utf-8"))
    result = []
    for source in receipt["rows"]:
        replay = json.loads(Path(source["path"]).read_text(encoding="utf-8"))
        for teacher in source["teachers"]:
            seat = int(teacher["seat"])
            actions = [replay["steps"][turn + 1][seat].get("action") for turn in range(719)]
            result.append({
                "route_id": f"{teacher['team']}__{source['episode_id']}__s{seat}",
                "teacher": teacher["team"],
                "episode_id": int(source["episode_id"]),
                "source_seat": seat,
                "source_seed": int(source["seed"]),
                "actions": actions,
            })
    return result


def play(route: dict, opponent_name: str, seed: int, seat: int) -> dict:
    candidate = load(BASE, f"candidate_{route['route_id']}_{opponent_name}_{seed}_{seat}")
    candidate.module._V119_CENTER_ROUTE = route["actions"]
    opponent = load(OPPONENTS[opponent_name], f"{opponent_name}_{route['route_id']}_{seed}_{seat}")
    agents = [opponent, opponent]
    agents[seat] = candidate
    game = kagsim.Game(seed)
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        game.step(agents[0](observations[0]), agents[1](observations[1]))
    rewards = [float(game.reward(0)), float(game.reward(1))]
    own, other = rewards[seat], rewards[1 - seat]
    return {"opponent": opponent_name, "seed": seed, "seat": seat, "own_reward": own, "opponent_reward": other, "margin": own - other, "outcome": "win" if own > other else "tie" if own == other else "loss"}


def main() -> int:
    summaries = []
    for index, route in enumerate(routes(), 1):
        rows = [play(route, opponent, seed, seat) for opponent in OPPONENTS for seed in SEEDS for seat in (0, 1)]
        by_opponent = {}
        for opponent in OPPONENTS:
            sample = [row for row in rows if row["opponent"] == opponent]
            wins = sum(row["outcome"] == "win" for row in sample)
            ties = sum(row["outcome"] == "tie" for row in sample)
            by_opponent[opponent] = {"games": len(sample), "wins_ties_losses": [wins, ties, len(sample) - wins - ties], "win_rate": wins / len(sample), "mean_margin": sum(row["margin"] for row in sample) / len(sample), "mean_own_reward": sum(row["own_reward"] for row in sample) / len(sample)}
        summary = {key: route[key] for key in ("route_id", "teacher", "episode_id", "source_seat", "source_seed")}
        summary["by_opponent"] = by_opponent
        summary["min_win_rate"] = min(value["win_rate"] for value in by_opponent.values())
        summary["rows"] = rows
        summaries.append(summary)
        print(json.dumps({"progress": f"{index}/19", "route": route["route_id"], "min_win_rate": summary["min_win_rate"], "by_opponent": by_opponent}, ensure_ascii=False), flush=True)
    summaries.sort(key=lambda row: (row["min_win_rate"], sum(value["mean_margin"] for value in row["by_opponent"].values())), reverse=True)
    report = {"schema": "kaggriculture-v120-top5-route-screen-v1", "engine": str(kagsim.ENGINE_VERSION), "seeds": list(SEEDS), "dual_seat": True, "opponents": list(OPPONENTS), "routes": summaries}
    (HERE / "route_screen_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"best": {key: summaries[0][key] for key in ("route_id", "teacher", "episode_id", "min_win_rate", "by_opponent")}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
