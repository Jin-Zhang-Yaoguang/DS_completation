#!/usr/bin/env python3
"""Audit whether V76 exposes the structure required by the V83 hypothesis.

V83 proposed moving a product purchase across an adjacent animal purchase when
cash and shed capacity jointly made that ordering safer.  This preconstruction
audit uses synthetic QA seeds only and counts the parent market queue shapes;
it does not estimate strategy strength and consumes no official Replay source.
"""

from __future__ import annotations

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


PARENT = MODEL / "v76_adjacent_safe_buy_lead/main.py"
OPPONENTS = {
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}
SEEDS = range(82301, 82305)


def main() -> None:
    registry = Registry(path=HERE / "audit_registry.json", models={}, raw={})
    decision_calls = 0
    adjacent_buy_animal_product = 0
    adjacent_product_animal = 0
    games = 0
    examples: list[dict[str, object]] = []
    for family, opponent_path in OPPONENTS.items():
        for seed in SEEDS:
            for seat in (0, 1):
                parent = create_agent(registry, {
                    "id": f"parent_{family}_{seed}_{seat}_{os.getpid()}",
                    "kind": "python", "path": str(PARENT), "entrypoint": "agent",
                })
                rival = create_agent(registry, {
                    "id": f"rival_{family}_{seed}_{seat}_{os.getpid()}",
                    "kind": "python", "path": str(opponent_path), "entrypoint": "agent",
                })
                agents = [None, None]
                agents[seat], agents[1 - seat] = parent, rival
                game = kagsim.Game(seed)
                while not game.done:
                    obs = [game.observe(0), game.observe(1)]
                    actions = [agents[0](obs[0]), agents[1](obs[1])]
                    market = list(actions[seat].get("market") or [])
                    decision_calls += 1
                    for left, right in zip(market, market[1:]):
                        lop = left[0] if left else "PASS"
                        rop = right[0] if right else "PASS"
                        if lop == "BUY_ANIMAL" and rop == "BUY_PRODUCT":
                            adjacent_buy_animal_product += 1
                            if len(examples) < 8:
                                examples.append({"family": family, "seed": seed,
                                                 "seat": seat, "step": game.step_count,
                                                 "left": left, "right": right})
                        if lop == "BUY_PRODUCT" and rop == "BUY_ANIMAL":
                            adjacent_product_animal += 1
                    game.step(actions[0], actions[1])
                games += 1
    payload = {
        "schema": "kaggriculture-v83-parent-structure-audit-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "synthetic_seeds": [min(SEEDS), max(SEEDS)],
        "opponents": list(OPPONENTS),
        "both_seats": True,
        "games": games,
        "decision_calls": decision_calls,
        "official_replay_sources": 0,
        "adjacent_buy_animal_then_buy_product": adjacent_buy_animal_product,
        "adjacent_buy_product_then_buy_animal": adjacent_product_animal,
        "required_structure_present": adjacent_buy_animal_product > 0,
        "examples": examples,
    }
    (HERE / "parent_structure_audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
