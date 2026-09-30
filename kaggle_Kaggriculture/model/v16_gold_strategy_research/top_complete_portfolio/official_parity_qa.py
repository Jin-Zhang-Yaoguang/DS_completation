#!/usr/bin/env python3
"""CPP L1 versus official Kaggriculture interpreter parity for the router."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(ROOT), str(HERE), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
from portfolio_policy import make_agent


SEEDS = (23001, 23007)


def pair(seed, seat):
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    candidate = make_agent("router")
    opponent = create_agent(registry, {
        "id": f"parity_kawa_{seed}_{seat}_{random.random()}", "kind": "python",
        "path": str(MODEL / "v8_kawa_lead2_slot" / "main.py"), "entrypoint": "agent",
    })
    return [candidate, opponent] if seat == 0 else [opponent, candidate]


def cpp(seed, seat):
    agents = pair(seed, seat)
    game = kagsim.Game(seed)
    calls = [0, 0]
    while not game.done:
        actions = []
        for player in (0, 1):
            actions.append(agents[player](game.observe(player)))
            calls[player] += 1
        game.step(*actions)
    return [float(game.reward(0)), float(game.reward(1))], calls


def official(seed, seat):
    import numpy as np
    from kaggle_environments import make
    random.seed(seed * 104729 + seat)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    agents = pair(seed, seat)
    calls = [0, 0]
    wrapped = []
    for index, policy in enumerate(agents):
        def call(obs, config=None, policy=policy, index=index):
            calls[index] += 1
            return policy(obs, config)
        wrapped.append(call)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run(wrapped)
    return [float(state.reward or 0) for state in env.state], calls, [str(state.status) for state in env.state]


def main() -> int:
    rows = []
    for seed in SEEDS:
        for seat in (0, 1):
            cpp_reward, cpp_calls = cpp(seed, seat)
            official_reward, official_calls, statuses = official(seed, seat)
            rows.append({
                "seed": seed, "candidate_seat": seat,
                "cpp_rewards": cpp_reward, "official_rewards": official_reward,
                "exact": cpp_reward == official_reward,
                "cpp_calls": cpp_calls, "official_calls": official_calls,
                "statuses": statuses,
            })
    result = {
        "status": "CPP_OFFICIAL_EXACT_PARITY_QA",
        "engine": str(kagsim.ENGINE_VERSION),
        "games": len(rows), "exact_games": sum(row["exact"] for row in rows),
        "rows": rows,
    }
    output = HERE / "official_parity_results.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["exact_games"] == result["games"] and all(row["statuses"] == ["DONE", "DONE"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

