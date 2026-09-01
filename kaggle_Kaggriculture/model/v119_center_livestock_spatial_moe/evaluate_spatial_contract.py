#!/usr/bin/env python3
"""Evaluate V119's champion-derived spatial contract against the frozen source tape."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore  # noqa: E402
from agent_factory import Registry, create_agent  # type: ignore  # noqa: E402


SEED = 1385806507
SOURCE_REPLAY = HERE / "evidence/episode-103982514-replay.json"
V118 = MODEL / "v118_v76_yarn_reveal_liquidity_moe/main.py"
V119 = HERE / "main.py"
SHED_ACCESS = ((3, 3), (4, 3), (3, 4), (4, 4))
TOP_TWO = {(x, y) for y in (0, 1) for x in range(5)}
CHECKPOINTS = (71, 272, 346, 557, 719)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path, model_id: str):
    registry = Registry(path=HERE / "spatial_contract_registry.json", models={}, raw={})
    return create_agent(registry, {
        "id": model_id,
        "kind": "python",
        "path": str(path),
        "entrypoint": "agent",
    })


def distance(x: int, y: int) -> int:
    return min(abs(x - sx) + abs(y - sy) for sx, sy in SHED_ACCESS)


def frame_metrics(farm: dict) -> dict:
    large_animals = []
    top_two = []
    for y, row in enumerate(farm.get("tiles") or []):
        for x, tile in enumerate(row or []):
            if not isinstance(tile, dict):
                continue
            animal = str(tile.get("animal") or "")
            if animal in {"COW", "SHEEP"}:
                large_animals.append({
                    "x": x,
                    "y": y,
                    "animal": animal,
                    "shed_distance": distance(x, y),
                })
            if (x, y) in TOP_TWO and tile.get("kind") == "PLANT":
                top_two.append({
                    "x": x,
                    "y": y,
                    "crop": tile.get("crop"),
                    "yield_units": int(tile.get("yield_units", 0) or 0),
                })
    return {
        "money": float(farm.get("money", 0) or 0),
        "large_animal_count": len(large_animals),
        "remote_large_animal_count": sum(row["shed_distance"] > 2 for row in large_animals),
        "large_animals": large_animals,
        "top_two_wheat_at_least_two": sum(
            row["crop"] == "WHEAT" and row["yield_units"] >= 2 for row in top_two
        ),
        "top_two": top_two,
    }


def play(path: Path, candidate_seat: int, replay: dict) -> dict:
    candidate = load(path, f"{path.parent.name}_{candidate_seat}")
    opponent_tape = [copy.deepcopy(step[0].get("action") or {}) for step in replay["steps"][1:720]]
    source_candidate_tape = [copy.deepcopy(step[1].get("action") or {}) for step in replay["steps"][1:720]]
    game = kagsim.Game(SEED)
    frames = {}
    first_top_two_harvest = {}
    action_exact = 0
    production_exact = 0
    turns = 0
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        step = int(observations[0]["step"])
        own_obs = observations[candidate_seat]
        own_action = candidate(own_obs)
        source_action = source_candidate_tape[step]
        action_exact += own_action == source_action
        production_exact += (
            own_action.get("farmer") == source_action.get("farmer")
            and own_action.get("hands") == source_action.get("hands")
        )

        farm = own_obs["farms"][candidate_seat]
        units = [
            (farm.get("farmer") or [0, 0], own_action.get("farmer") or ["PASS"]),
            *list(zip(farm.get("hands") or [], own_action.get("hands") or [])),
        ]
        for position, order in units:
            if not order or order[0] != "HARVEST":
                continue
            x, y = int(position[0]), int(position[1])
            if (x, y) not in TOP_TWO or (x, y) in first_top_two_harvest:
                continue
            tile = farm["tiles"][y][x]
            if isinstance(tile, dict) and tile.get("crop") == "WHEAT":
                first_top_two_harvest[(x, y)] = {
                    "step": step,
                    "yield_units_before_action": int(tile.get("yield_units", 0) or 0),
                }

        actions = [None, None]
        actions[candidate_seat] = own_action
        actions[1 - candidate_seat] = copy.deepcopy(opponent_tape[step])
        game.step(*actions)
        turns += 1
        if step + 1 in CHECKPOINTS:
            frames[str(step + 1)] = frame_metrics(game.observe(candidate_seat)["farms"][candidate_seat])

    rewards = [float(game.reward(0)), float(game.reward(1))]
    own_reward = rewards[candidate_seat]
    opponent_reward = rewards[1 - candidate_seat]
    return {
        "candidate_seat": candidate_seat,
        "turns": turns,
        "rewards": rewards,
        "own_reward": own_reward,
        "opponent_reward": opponent_reward,
        "margin": own_reward - opponent_reward,
        "action_exact_vs_source": action_exact,
        "production_action_exact_vs_source": production_exact,
        "first_top_two_harvest": [
            {"x": x, "y": y, **value}
            for (x, y), value in sorted(first_top_two_harvest.items(), key=lambda item: (item[0][1], item[0][0]))
        ],
        "frames": frames,
    }


def main() -> int:
    replay = json.loads(SOURCE_REPLAY.read_text(encoding="utf-8"))
    baseline = [play(V118, seat, replay) for seat in (0, 1)]
    candidate = [play(V119, seat, replay) for seat in (0, 1)]
    gates = {
        "engine_1_32_7": str(kagsim.ENGINE_VERSION) == "1.32.7",
        "all_719_calls": all(row["turns"] == 719 for row in baseline + candidate),
        "opening_top_two_rows_are_ten_wheat_at_yield_2_plus": all(
            row["frames"]["71"]["top_two_wheat_at_least_two"] == 10 for row in candidate
        ),
        "all_ten_opening_wheat_first_harvest_at_yield_2_plus": all(
            len(row["first_top_two_harvest"]) == 10
            and min(value["yield_units_before_action"] for value in row["first_top_two_harvest"]) >= 2
            for row in candidate
        ),
        "day12_primary_herd_is_11_and_all_within_two_tiles": all(
            row["frames"]["272"]["large_animal_count"] == 11
            and row["frames"]["272"]["remote_large_animal_count"] == 0
            for row in candidate
        ),
        "v118_day12_remote_defect_reproduced": all(
            row["frames"]["272"]["remote_large_animal_count"] == 3 for row in baseline
        ),
        "dual_seat_margin_flips_loss_to_win": all(
            before["margin"] < 0 < after["margin"]
            for before, after in zip(baseline, candidate)
        ),
        "dual_seat_own_reward_improves": all(
            after["own_reward"] > before["own_reward"]
            for before, after in zip(baseline, candidate)
        ),
    }
    result = {
        "schema": "kaggriculture-v119-spatial-contract-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "source": {
            "episode_id": 103982514,
            "seed": SEED,
            "teams": replay["info"]["TeamNames"],
            "replay_sha256": sha256(SOURCE_REPLAY),
            "historical_opponent_actions_used": True,
            "purpose": "same-seed fixed-opponent causal comparison and source-route parity",
        },
        "baseline_v118": baseline,
        "candidate_v119": candidate,
        "gates": gates,
        "gate": "PASS" if all(gates.values()) else "FAIL",
    }
    (HERE / "spatial_contract_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"gate": result["gate"], "gates": gates}, ensure_ascii=False, indent=2))
    return 0 if result["gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
