#!/usr/bin/env python3
"""Audit action support for the next post-V66 market mechanism."""

from __future__ import annotations

from collections import Counter
import concurrent.futures
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore

OPPONENTS = {
    "v19": MODEL / "v19_hierarchical_moe/main.py",
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v33": MODEL / "v33_demand_gap_horizon4/main.py",
    "v34": MODEL / "v34_demand_boundary_preempt/main.py",
    "v37": MODEL / "v37_preterminal_boundary_preempt/main.py",
    "v46": MODEL / "v46_full_terminal_front_run/main.py",
    "v51": MODEL / "v51_post_action_terminal_sell/main.py",
    "v52": MODEL / "v52_terminal_route_acceleration/main.py",
    "v53": MODEL / "v53_terminal_access_flush/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
}
SEEDS = range(70001, 70009)


def play(task):
    family, seed, seat = task
    registry = Registry(path=HERE / "audit_registry.json", models={}, raw={})
    own = create_agent(registry, {"id": f"own_{family}_{seed}_{seat}_{os.getpid()}", "kind": "python", "path": str(HERE / "main.py"), "entrypoint": "agent"})
    rival = create_agent(registry, {"id": f"opp_{family}_{seed}_{seat}_{os.getpid()}", "kind": "python", "path": str(OPPONENTS[family]), "entrypoint": "agent"})
    agents = [None, None]
    agents[seat], agents[1 - seat] = own, rival
    game = kagsim.Game(seed)
    pairs, buy_products, mixed_sell_buys, multi_sells = Counter(), Counter(), Counter(), Counter()
    action_turns = 0
    while not game.done:
        obs = [game.observe(0), game.observe(1)]
        actions = [agents[0](obs[0]), agents[1](obs[1])]
        market = [order for order in (actions[seat].get("market") or []) if isinstance(order, list) and order]
        if market:
            action_turns += 1
        for left, right in zip(market, market[1:]):
            pairs[(str(left[0]), str(right[0]))] += 1
        buys = [str(order[1]) for order in market if order[0] == "BUY_PRODUCT" and len(order) >= 3 and int(order[2] or 0) > 0]
        sells = [str(order[1]) for order in market if order[0] == "SELL" and len(order) >= 3 and int(order[2] or 0) > 0]
        if len(buys) >= 2:
            buy_products[tuple(buys)] += 1
        if buys and sells:
            mixed_sell_buys[(tuple(buys), tuple(sells))] += 1
        if len(sells) >= 2:
            multi_sells[tuple(sells)] += 1
        game.step(actions[0], actions[1])
    return {"family": family, "seed": seed, "seat": seat, "action_turns": action_turns,
            "pairs": {str(k): v for k, v in pairs.items()}, "buy_products": {str(k): v for k, v in buy_products.items()},
            "mixed_sell_buys": {str(k): v for k, v in mixed_sell_buys.items()},
            "multi_sells": {str(k): v for k, v in multi_sells.items()}}


def main():
    tasks = [(family, seed, seat) for family in OPPONENTS for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    totals = {name: Counter() for name in ("pairs", "buy_products", "mixed_sell_buys", "multi_sells")}
    for row in rows:
        for name in totals:
            totals[name].update(row[name])
    result = {"games": len(rows), "seeds": list(SEEDS),
              **{name: dict(counter.most_common()) for name, counter in totals.items()}}
    (HERE / "market_pattern_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
