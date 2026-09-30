#!/usr/bin/env python3
"""Reproducible L1 speed and conservative S2 mechanism pilot.

This is a research harness, not a submission agent.  In particular the S2
controller below is deliberately opponent-blind.  Its purpose is to verify:

1. cppsim L1 produces the same rewards as kaggle-environments for live Python
   agents while measuring the real closed-loop speedup;
2. a tightly gated town-drain WHEAT roundtrip returns the exact integer profit
   predicted by the market formula against no-WHEAT-flow controls;
3. fixed top-player tapes can break the no-interference assumption, so an
   opponent-flow gate is required before this mechanism can be promoted.

Run from the repository root with the project Python 3.12 environment:

    .venv/bin/python \
      kaggle_Kaggriculture/model/v16_gold_strategy_research/run_l1_s2_pilot.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
MODEL = REPO / "kaggle_Kaggriculture" / "model"
A2_PATH = MODEL / "v1_adaptive_market" / "main.py"
CPPSIM = (
    MODEL
    / "community_research"
    / "2026-08-26"
    / "live_cli"
    / "external_repos"
    / "kaggriculture-cppsim"
)
ISLAND_GA = (
    MODEL
    / "community_research"
    / "2026-08-26"
    / "live_cli"
    / "external_repos"
    / "kaggriculture-island-ga"
)
EPISODES = (
    REPO
    / "kaggle_Kaggriculture"
    / "model_data"
    / "kaggriculture_episodes_index"
    / "date=2026-08-25"
    / "data"
)
PASS_ACTION = {"farmer": ["PASS"], "hands": [], "market": []}


def _load_cppsim() -> object:
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError(f"cppsim extension is not built under {CPPSIM / 'build'}")
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore

    return kagsim


KAGSIM = _load_cppsim()
sys.path.insert(0, str(ISLAND_GA))


_MODULE_SERIAL = 0


def load_a2(tag: str):
    global _MODULE_SERIAL
    _MODULE_SERIAL += 1
    name = f"a2_{tag}_{_MODULE_SERIAL}"
    spec = importlib.util.spec_from_file_location(name, A2_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {A2_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unit_orders(action: dict) -> list:
    return [action.get("farmer", ["PASS"]), *(action.get("hands") or [])]


def has_unit_op(action: dict, ops: set[str]) -> bool:
    return any(
        isinstance(order, list) and order and order[0] in ops
        for order in unit_orders(action)
    )


class S2Pilot:
    """Opponent-blind, one-step town-drain controller for mechanism tests."""

    def __init__(
        self,
        parent_module,
        *,
        demand_floor: int = 2,
        q_cap: int = 80,
        min_profit: int = 2,
        cash_floor: int = 3000,
    ) -> None:
        self.parent = parent_module
        self.demand_floor = demand_floor
        self.q_cap = q_cap
        self.min_profit = min_profit
        self.cash_floor = cash_floor
        self.pending = {0: None, 1: None}
        self.trades = {0: [], 1: []}
        self.unwind_violations = {0: 0, 1: 0}

    def _profit(self, inventory: int, quantity: int, demand: int) -> int:
        price = self.parent._market_price
        cost = sum(
            price("WHEAT", level)
            for level in range(inventory - quantity, inventory)
        )
        revenue = sum(
            price("WHEAT", level)
            for level in range(
                inventory - quantity - demand,
                inventory - demand,
            )
        )
        return int(revenue - cost)

    def act(self, observation: dict) -> dict:
        parent = self.parent
        seat = int(observation["player"])
        step = int(observation["step"])
        action = parent.agent(observation)
        if step == 0:
            self.pending[seat] = None
            self.trades[seat] = []
            self.unwind_violations[seat] = 0

        pending = self.pending[seat]
        if pending is not None:
            available = int(
                observation["private"]["shed"].get("WHEAT", 0) or 0
            ) - parent._v17_pickup_reserve(action, "WHEAT")
            sold = max(0, min(available, pending["q"]))
            if sold < pending["q"]:
                self.unwind_violations[seat] += 1
            if sold:
                # The entry gate predicts an empty parent queue.  Prepending is
                # fail-safe if a dynamic parent valve nevertheless emits one:
                # restore working capital before the parent's purchases.
                pending["parent_exit_orders"] = len(action.get("market") or [])
                action["market"] = [
                    ["SELL", "WHEAT", sold],
                    *(action.get("market") or []),
                ][:10]
            pending["sold"] = sold
            self.trades[seat].append(pending)
            self.pending[seat] = None
            return action

        if step >= 718 or step % 4 != 0 or action.get("market"):
            return action
        demand = parent._v17_town_demand_at(observation, "WHEAT", step)
        if demand < self.demand_floor:
            return action

        next_base = parent._ACTIONS[step + 1]
        if next_base.get("market") or has_unit_op(
            next_base, {"PICKUP", "DROP", "PLACE"}
        ):
            return action

        projected = parent._projected_shed(observation, action)
        room = max(
            0,
            100 - sum(max(0, int(value or 0)) for value in projected.values()),
        )
        money = float(observation["farms"][seat]["money"])
        inventory = int(observation["market"]["inventory"]["WHEAT"])
        candidates = []
        for quantity in range(1, min(self.q_cap, room) + 1):
            cost = sum(
                parent._market_price("WHEAT", level)
                for level in range(inventory - quantity, inventory)
            )
            if money - cost < self.cash_floor:
                continue
            profit = self._profit(inventory, quantity, demand)
            candidates.append((profit, quantity, cost))
        if not candidates:
            return action

        best_profit = max(row[0] for row in candidates)
        best_quantity = min(row[1] for row in candidates if row[0] == best_profit)
        if best_profit < self.min_profit:
            return action
        best_cost = next(row[2] for row in candidates if row[1] == best_quantity)
        action["market"] = [["BUY_PRODUCT", "WHEAT", best_quantity]]
        self.pending[seat] = {
            "entry_step": step,
            "q": best_quantity,
            "demand": demand,
            "theoretical_profit": best_profit,
            "working_capital": best_cost,
            "sold": 0,
            "parent_exit_orders": None,
        }
        return action


def play_cpp_agents(seed: int, agent0, agent1) -> tuple[float, float]:
    game = KAGSIM.Game(int(seed))
    while not game.done:
        game.step(agent0(game.observe(0)), agent1(game.observe(1)))
    return float(game.reward(0)), float(game.reward(1))


def a2_official_bank(module, seed: int) -> float:
    from kaggle_environments import make

    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": int(seed)},
    )
    env.reset(2)
    while not env.done:
        env.step([module.agent(env.state[0].observation), dict(PASS_ACTION)])
    return float(env.state[0].reward or 0)


def a2_cpp_bank(module, seed: int) -> float:
    game = KAGSIM.Game(int(seed))
    while not game.done:
        game.step(module.agent(game.observe(0)), dict(PASS_ACTION))
    return float(game.reward(0))


def speed_benchmark() -> dict:
    from islandga.compiler import compile_spec
    from islandga.evaluate import bank_of
    from islandga.executor import make_agent
    from islandga.genome import species_envelope

    blueprint = compile_spec(species_envelope())
    island_seeds = (5, 11, 13, 23, 29, 47, 61, 83)

    official_started = time.perf_counter()
    island_official = [bank_of(blueprint, seed) for seed in island_seeds]
    island_official_seconds = time.perf_counter() - official_started

    def cpp_island_bank(seed: int) -> float:
        agent = make_agent(blueprint)
        game = KAGSIM.Game(seed)
        while not game.done:
            game.step(agent(game.observe(0)), dict(PASS_ACTION))
        return float(game.reward(0))

    cpp_started = time.perf_counter()
    island_cpp = [cpp_island_bank(seed) for seed in island_seeds]
    island_cpp_seconds = time.perf_counter() - cpp_started

    a2_seeds = (5, 11, 13, 23)
    official_module = load_a2("speed_official")
    cpp_module = load_a2("speed_cpp")
    official_started = time.perf_counter()
    a2_official = [a2_official_bank(official_module, seed) for seed in a2_seeds]
    a2_official_seconds = time.perf_counter() - official_started
    cpp_started = time.perf_counter()
    a2_cpp = [a2_cpp_bank(cpp_module, seed) for seed in a2_seeds]
    a2_cpp_seconds = time.perf_counter() - cpp_started

    return {
        "engine": KAGSIM.ENGINE_VERSION,
        "island_reference": {
            "seeds": list(island_seeds),
            "official_rewards": island_official,
            "cpp_rewards": island_cpp,
            "reward_exact": island_official == island_cpp,
            "official_seconds": island_official_seconds,
            "cpp_seconds": island_cpp_seconds,
            "official_eps": len(island_seeds) / island_official_seconds,
            "cpp_eps": len(island_seeds) / island_cpp_seconds,
            "speedup": island_official_seconds / island_cpp_seconds,
        },
        "a2": {
            "seeds": list(a2_seeds),
            "official_rewards": a2_official,
            "cpp_rewards": a2_cpp,
            "reward_exact": a2_official == a2_cpp,
            "official_seconds": a2_official_seconds,
            "cpp_seconds": a2_cpp_seconds,
            "official_eps": len(a2_seeds) / a2_official_seconds,
            "cpp_eps": len(a2_seeds) / a2_cpp_seconds,
            "speedup": a2_official_seconds / a2_cpp_seconds,
        },
    }


def _summarize_paired(rows: list[dict]) -> dict:
    deltas = [row["own_delta"] for row in rows]
    margin_deltas = [row["margin_delta"] for row in rows]
    return {
        "comparisons": len(rows),
        "own_positive": sum(value > 0 for value in deltas),
        "own_zero": sum(value == 0 for value in deltas),
        "own_negative": sum(value < 0 for value in deltas),
        "own_delta_mean": statistics.mean(deltas),
        "own_delta_median": statistics.median(deltas),
        "own_delta_min": min(deltas),
        "own_delta_max": max(deltas),
        "margin_positive": sum(value > 0 for value in margin_deltas),
        "margin_zero": sum(value == 0 for value in margin_deltas),
        "margin_negative": sum(value < 0 for value in margin_deltas),
        "margin_delta_mean": statistics.mean(margin_deltas),
        "trades": sum(row["trades"] for row in rows),
        "theoretical_profit": sum(row["theoretical_profit"] for row in rows),
        "actual_own_delta": sum(deltas),
        "unwind_violations": sum(row["unwind_violations"] for row in rows),
    }


def s2_vs_idle(seed_count: int) -> dict:
    baseline_module = load_a2("idle_base")
    candidate_module = load_a2("idle_s2")
    rows = []
    for seed in range(seed_count):
        baseline, _ = play_cpp_agents(
            seed,
            baseline_module.agent,
            lambda _obs: dict(PASS_ACTION),
        )
        controller = S2Pilot(candidate_module)
        candidate, _ = play_cpp_agents(
            seed,
            controller.act,
            lambda _obs: dict(PASS_ACTION),
        )
        trades = controller.trades[0]
        rows.append(
            {
                "seed": seed,
                "baseline": baseline,
                "candidate": candidate,
                "own_delta": candidate - baseline,
                "margin_delta": candidate - baseline,
                "trades": len(trades),
                "theoretical_profit": sum(
                    trade["theoretical_profit"] for trade in trades
                ),
                "unwind_violations": controller.unwind_violations[0],
            }
        )
    return {"summary": _summarize_paired(rows), "rows": rows}


def s2_vs_a2(seed_count: int) -> dict:
    baseline0 = load_a2("mirror_base0")
    baseline1 = load_a2("mirror_base1")
    candidate_modules = [load_a2("mirror_s2_0"), load_a2("mirror_s2_1")]
    opponent_modules = [load_a2("mirror_opp_0"), load_a2("mirror_opp_1")]
    rows = []
    for seed in range(seed_count):
        baseline_rewards = play_cpp_agents(
            seed, baseline0.agent, baseline1.agent
        )
        for seat in (0, 1):
            controller = S2Pilot(candidate_modules[seat])
            opponent = opponent_modules[seat]
            if seat == 0:
                candidate_rewards = play_cpp_agents(
                    seed, controller.act, opponent.agent
                )
            else:
                candidate_rewards = play_cpp_agents(
                    seed, opponent.agent, controller.act
                )
            other = 1 - seat
            trades = controller.trades[seat]
            rows.append(
                {
                    "seed": seed,
                    "seat": seat,
                    "baseline_own": baseline_rewards[seat],
                    "baseline_opponent": baseline_rewards[other],
                    "candidate_own": candidate_rewards[seat],
                    "candidate_opponent": candidate_rewards[other],
                    "own_delta": candidate_rewards[seat]
                    - baseline_rewards[seat],
                    "opponent_delta": candidate_rewards[other]
                    - baseline_rewards[other],
                    "margin_delta": (
                        candidate_rewards[seat] - candidate_rewards[other]
                    )
                    - (baseline_rewards[seat] - baseline_rewards[other]),
                    "trades": len(trades),
                    "theoretical_profit": sum(
                        trade["theoretical_profit"] for trade in trades
                    ),
                    "unwind_violations": controller.unwind_violations[seat],
                }
            )
    summary = _summarize_paired(rows)
    summary["baseline_wins"] = sum(
        row["baseline_own"] > row["baseline_opponent"] for row in rows
    )
    summary["baseline_ties"] = sum(
        row["baseline_own"] == row["baseline_opponent"] for row in rows
    )
    summary["candidate_wins"] = sum(
        row["candidate_own"] > row["candidate_opponent"] for row in rows
    )
    summary["candidate_ties"] = sum(
        row["candidate_own"] == row["candidate_opponent"] for row in rows
    )
    return {"summary": summary, "rows": rows}


def play_against_fixed_replay(
    replay: dict, own_seat: int, module, controller: S2Pilot | None
) -> tuple[tuple[float, float], list[dict], int]:
    fixed = [
        [row[seat].get("action") or {} for row in replay["steps"][1:720]]
        for seat in (0, 1)
    ]
    game = KAGSIM.Game(int(replay["info"]["seed"]))
    for step in range(719):
        actions = [None, None]
        actions[1 - own_seat] = fixed[1 - own_seat][step]
        observation = game.observe(own_seat)
        actions[own_seat] = (
            controller.act(observation)
            if controller is not None
            else module.agent(observation)
        )
        game.step(actions[0], actions[1])
    trades = [] if controller is None else controller.trades[own_seat]
    violations = 0 if controller is None else controller.unwind_violations[own_seat]
    return (float(game.reward(0)), float(game.reward(1))), trades, violations


def s2_vs_fixed_replays() -> dict:
    episode_ids = ("99288516", "99288626", "99512062", "99594187", "99628090")
    baseline_module = load_a2("fixed_base")
    candidate_module = load_a2("fixed_s2")
    rows = []
    for episode_id in episode_ids:
        path = EPISODES / f"{episode_id}.json"
        replay = json.loads(path.read_text())
        teams = replay["info"]["TeamNames"]
        for opponent_seat in (0, 1):
            own_seat = 1 - opponent_seat
            baseline, _, _ = play_against_fixed_replay(
                replay, own_seat, baseline_module, None
            )
            controller = S2Pilot(candidate_module)
            candidate, trades, violations = play_against_fixed_replay(
                replay, own_seat, candidate_module, controller
            )
            rows.append(
                {
                    "episode_id": episode_id,
                    "opponent": teams[opponent_seat],
                    "opponent_seat": opponent_seat,
                    "own_seat": own_seat,
                    "baseline_own": baseline[own_seat],
                    "baseline_opponent": baseline[opponent_seat],
                    "candidate_own": candidate[own_seat],
                    "candidate_opponent": candidate[opponent_seat],
                    "own_delta": candidate[own_seat] - baseline[own_seat],
                    "opponent_delta": candidate[opponent_seat]
                    - baseline[opponent_seat],
                    "margin_delta": (
                        candidate[own_seat] - candidate[opponent_seat]
                    )
                    - (baseline[own_seat] - baseline[opponent_seat]),
                    "trades": len(trades),
                    "theoretical_profit": sum(
                        trade["theoretical_profit"] for trade in trades
                    ),
                    "unwind_violations": violations,
                }
            )
    return {"summary": _summarize_paired(rows), "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("all", "speed", "idle", "a2", "fixed"),
        default="all",
    )
    parser.add_argument("--idle-seeds", type=int, default=40)
    parser.add_argument("--a2-seeds", type=int, default=20)
    args = parser.parse_args()

    result = {
        "status": "MECHANISM_PILOT_NOT_SUBMISSION_QUALIFIED",
        "opponent_blind": True,
        "cppsim_engine": KAGSIM.ENGINE_VERSION,
    }
    if args.mode in ("all", "speed"):
        result["speed"] = speed_benchmark()
    if args.mode in ("all", "idle"):
        result["s2_vs_idle"] = s2_vs_idle(args.idle_seeds)
    if args.mode in ("all", "a2"):
        result["s2_vs_a2"] = s2_vs_a2(args.a2_seeds)
    if args.mode in ("all", "fixed"):
        result["s2_vs_fixed_replays"] = s2_vs_fixed_replays()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
