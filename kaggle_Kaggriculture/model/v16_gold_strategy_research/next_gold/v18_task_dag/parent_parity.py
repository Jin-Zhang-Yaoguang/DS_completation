#!/usr/bin/env python3
"""Prove parent mode is action-identical to the frozen submitted V17 file."""

from __future__ import annotations

import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import policy  # noqa: E402
import task_dag  # noqa: E402


def main() -> None:
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    sys.path.insert(0, str(builds[-1]))
    sys.path.insert(0, str(FACTORY))
    import kagsim  # type: ignore
    from agent_factory import Registry, create_agent  # type: ignore

    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    opponent_path = MODEL / "v12_incumbent_r002" / "main.py"
    calls = mismatches = 0
    route_checks = {}
    for name in task_dag.ROUTES:
        actions, _ = task_dag.route_stream(name)
        expected = task_dag._FROZEN._PORT_YARN if name == "yarn" else task_dag._FROZEN._PORT_DEFAULT
        route_checks[name] = {"actions": len(actions), "mismatches": sum(a != b for a, b in zip(actions, expected))}
    episodes = []
    for seed in range(17000, 17004):
        for seat in (0, 1):
            game = kagsim.Game(seed)
            wrapped = policy.make_agent("parent")
            exact = task_dag.load_frozen_parent().agent
            opponent = create_agent(registry, {
                "id": f"parent_parity_{seed}_{seat}", "kind": "python",
                "path": str(opponent_path), "entrypoint": "agent",
            })
            while not game.done:
                obs = game.observe(seat)
                left, right = wrapped(obs), exact(obs)
                calls += 1
                mismatches += int(left != right)
                actions = [{}, {}]
                actions[seat], actions[1 - seat] = left, opponent(game.observe(1 - seat))
                game.step(actions[0], actions[1])
            episodes.append({"seed": seed, "seat": seat, "bank": float(game.reward(seat))})
    result = {
        "schema": "kaggriculture-v18-parent-parity-v1",
        "frozen_sha256": task_dag.FROZEN_SHA256,
        "engine": str(kagsim.ENGINE_VERSION), "episodes": len(episodes),
        "action_calls": calls, "action_mismatches": mismatches,
        "route_stream_checks": route_checks,
        "pass": mismatches == 0 and all(v["mismatches"] == 0 for v in route_checks.values()),
        "episode_detail": episodes,
    }
    (HERE / "parent_parity.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
