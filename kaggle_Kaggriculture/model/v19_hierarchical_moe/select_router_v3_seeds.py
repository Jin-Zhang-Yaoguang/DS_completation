#!/usr/bin/env python3
"""Freeze feature-stratified seeds without observing terminal outcomes."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MODEL = PROJECT / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(PROJECT.parent), str(HERE), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
from hierarchical_policy import make_agent


OPPONENT = MODEL / "v1_adaptive_market" / "main.py"
TARGET = ("BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT")
TARGET_COUNT = 8
BAKERY_CONTROL_COUNT = 12
GENERAL_CONTROL_COUNT = 24


def shops_only(seed: int) -> tuple[str, ...]:
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    parent = make_agent("parent")
    opponent = create_agent(registry, {
        "id": f"v19_seed_probe_{seed}_{uuid.uuid4().hex}", "kind": "python",
        "path": str(OPPONENT), "entrypoint": "agent",
    })
    game = kagsim.Game(seed)
    while game.step_count <= 216:
        observations = [game.observe(0), game.observe(1)]
        if game.step_count == 216:
            return tuple(str(value) for value in observations[0]["town"]["unlocked_shops"][:3])
        game.step(parent(observations[0]), opponent(observations[1]))
    raise RuntimeError(seed)


def main() -> int:
    target, bakery_control, general_control = [], [], []
    probes = []
    for seed in range(65000, 70000):
        shops = shops_only(seed)
        probes.append({"seed": seed, "shops": shops})
        if shops == TARGET and len(target) < TARGET_COUNT:
            target.append(seed)
        elif shops and shops[0] == "BAKERY" and len(bakery_control) < BAKERY_CONTROL_COUNT:
            bakery_control.append(seed)
        elif shops and shops[0] != "BAKERY" and len(general_control) < GENERAL_CONTROL_COUNT:
            general_control.append(seed)
        if len(probes) % 100 == 0:
            (HERE / "router_v3_seed_probe_progress.json").write_text(json.dumps({
                "last_seed": seed, "target": target,
                "bakery_control": bakery_control, "general_control": general_control,
                "probe_count": len(probes),
            }, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"probed {len(probes)} target={len(target)}", flush=True)
        if len(target) == TARGET_COUNT and len(bakery_control) == BAKERY_CONTROL_COUNT and len(general_control) == GENERAL_CONTROL_COUNT:
            break
    if len(target) < TARGET_COUNT:
        raise RuntimeError(f"insufficient target seeds: {len(target)}")
    selected = target + bakery_control + general_control
    result = {
        "schema": "kaggriculture-v19-router-v3-sparse-leaf-seeds-v2",
        "phase": "targeted_discovery",
        "frozen_before_terminal_outcomes": True,
        "probe_policy": "V17 parent vs adaptive_market, candidate seat 0, stop before step216 action",
        "target_sequence": list(TARGET),
        "target_count": TARGET_COUNT,
        "target_seeds": target,
        "bakery_control_seeds": bakery_control,
        "general_control_seeds": general_control,
        "seeds": selected,
        "opponent_families": ["adaptive_market", "anti_mirror", "incumbent_r002", "kawa_lead2"],
        "double_seat": True,
        "candidate_games": len(selected) * 4 * 2,
        "parent_games": len(selected) * 4 * 2,
        "probe_rows": probes,
    }
    (HERE / "router_v3_targeted_seeds.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "target_sequence", "target_seeds", "bakery_control_seeds", "general_control_seeds",
        "candidate_games", "parent_games",
    )}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
