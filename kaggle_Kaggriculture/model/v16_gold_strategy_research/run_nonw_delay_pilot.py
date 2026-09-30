#!/usr/bin/env python3
"""Paired L1 pilot for the non-WHEAT demand-delay planner."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import statistics
import sys
from pathlib import Path
from types import SimpleNamespace

from nonw_delay_planner import NON_WHEAT, DelayConfig, DemandDelayPlanner, canonical_action


REPO = Path(__file__).resolve().parents[3]
MODEL = REPO / "kaggle_Kaggriculture" / "model"
A2_PATH = MODEL / "v1_adaptive_market" / "main.py"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
RULES_PATH = MODEL / "v15_cleanroom_search" / "cleanroom" / "sessions" / "attempt_002" / "official_rules" / "kaggriculture.py"
PASS_ACTION = {"farmer": ["PASS"], "hands": [], "market": []}
_SERIAL = 0


def load_cppsim():
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError(f"cppsim extension missing under {CPPSIM / 'build'}")
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore

    return kagsim


KAGSIM = load_cppsim()


def load_rules():
    spec = importlib.util.spec_from_file_location("nonw_official_rules", RULES_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {RULES_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RULES = load_rules()


def load_a2(tag: str):
    global _SERIAL
    _SERIAL += 1
    spec = importlib.util.spec_from_file_location(f"a2_nonw_{tag}_{_SERIAL}", A2_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {A2_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def capture_live_a2(seed: int) -> tuple[list[list[dict]], list[list[dict]], tuple[float, float]]:
    modules = (load_a2(f"capture_{seed}_0"), load_a2(f"capture_{seed}_1"))
    streams: list[list[dict]] = [[], []]
    observations: list[list[dict]] = [[], []]
    game = KAGSIM.Game(int(seed))
    while not game.done:
        current = [copy.deepcopy(game.observe(seat)) for seat in (0, 1)]
        actions = [canonical_action(modules[seat].agent(current[seat])) for seat in (0, 1)]
        for seat in (0, 1):
            streams[seat].append(copy.deepcopy(actions[seat]))
            observations[seat].append(current[seat])
        game.step(actions[0], actions[1])
    return streams, observations, (float(game.reward(0)), float(game.reward(1)))


def replay_streams(seed: int, streams: list[list[dict]]) -> tuple[float, float]:
    game = KAGSIM.Game(int(seed))
    for step in range(len(streams[0])):
        game.step(copy.deepcopy(streams[0][step]), copy.deepcopy(streams[1][step]))
    return float(game.reward(0)), float(game.reward(1))


def public_farm_without_money(obs: dict, seat: int) -> str:
    farm = copy.deepcopy(obs["farms"][seat])
    farm.pop("money", None)
    return json.dumps(farm, sort_keys=True, separators=(",", ":"))


def projected_available(module, obs: dict, action: dict, item: str) -> int:
    projected = module._projected_shed(obs, action)
    return max(0, int(projected.get(item, 0) or 0) - module._v17_pickup_reserve(action, item))


def reduce_item(action: dict, item: str, quantity: int) -> dict:
    result = canonical_action(action)
    remaining = int(quantity)
    for order in reversed(result["market"]):
        if remaining <= 0:
            break
        if len(order) >= 3 and order[0] == "SELL" and order[1] == item:
            take = min(max(0, int(order[2] or 0)), remaining)
            order[2] = max(0, int(order[2] or 0)) - take
            remaining -= take
    return result


def add_item(action: dict, item: str, quantity: int) -> dict | None:
    result = canonical_action(action)
    existing = next(
        (order for order in result["market"] if len(order) >= 3 and order[0] == "SELL" and order[1] == item),
        None,
    )
    if existing is not None:
        existing[2] = max(0, int(existing[2] or 0)) + int(quantity)
    elif len(result["market"]) < 10:
        result["market"].append(["SELL", item, int(quantity)])
    else:
        return None
    return result


def simulate_item_market(module, inventory: int, actions: list[dict], available: list[int], item: str) -> tuple[list[int], int]:
    revenue = [0, 0]
    remaining_stock = [max(0, int(value)) for value in available]
    queues = [action.get("market", [])[:10] for action in actions]
    for slot in range(max(len(queues[0]), len(queues[1]))):
        quantities = [0, 0]
        for seat in (0, 1):
            if slot >= len(queues[seat]):
                continue
            order = queues[seat][slot]
            if len(order) >= 3 and order[0] == "SELL" and order[1] == item:
                quantities[seat] = min(max(0, int(order[2] or 0)), remaining_stock[seat])
        for unit in range(max(quantities)):
            quote = int(module._market_price(item, inventory))
            commits = 0
            for seat in (0, 1):
                if unit < quantities[seat]:
                    revenue[seat] += quote
                    remaining_stock[seat] -= 1
                    commits += 1
            if quote > 1:
                inventory += commits
    return revenue, inventory


def oracle_decisions(
    module,
    actual_obs: dict,
    baseline_observations: list[list[dict]],
    streams: list[list[dict]],
    step: int,
    own_seat: int,
    config: DelayConfig,
) -> dict[str, tuple[int, int]]:
    if step + 1 >= len(streams[0]) or step % 4 != 0:
        return {}
    other = 1 - own_seat
    own_now = canonical_action(streams[own_seat][step])
    opp_now = canonical_action(streams[other][step])
    own_next = canonical_action(streams[own_seat][step + 1])
    opp_next = canonical_action(streams[other][step + 1])
    result: dict[str, tuple[int, int]] = {}
    for item in NON_WHEAT:
        requested = sum(
            max(0, int(order[2] or 0))
            for order in own_now["market"]
            if len(order) >= 3 and order[0] == "SELL" and order[1] == item
        )
        demand = int(module._v17_town_demand_at(actual_obs, item, step))
        if requested <= 0 or demand <= 0:
            continue
        if module._v17_pickup_reserve(own_next, item) > 0:
            continue
        own_available_now = projected_available(module, baseline_observations[own_seat][step], own_now, item)
        opp_available_now = projected_available(module, baseline_observations[other][step], opp_now, item)
        max_quantity = min(requested, own_available_now, config.max_batch)
        if max_quantity <= 0:
            continue
        base_next_available = projected_available(module, baseline_observations[own_seat][step + 1], own_next, item)
        opp_next_available = projected_available(module, baseline_observations[other][step + 1], opp_next, item)
        start_inventory = int(actual_obs["market"]["inventory"][item])
        base_now_revenue, base_inventory = simulate_item_market(
            module,
            start_inventory,
            [own_now, opp_now] if own_seat == 0 else [opp_now, own_now],
            [own_available_now, opp_available_now] if own_seat == 0 else [opp_available_now, own_available_now],
            item,
        )
        base_inventory -= demand
        base_next_revenue, _ = simulate_item_market(
            module,
            base_inventory,
            [own_next, opp_next] if own_seat == 0 else [opp_next, own_next],
            [base_next_available, opp_next_available] if own_seat == 0 else [opp_next_available, base_next_available],
            item,
        )
        base_own = base_now_revenue[own_seat] + base_next_revenue[own_seat]
        base_opp = base_now_revenue[other] + base_next_revenue[other]
        best = None
        for quantity in range(1, max_quantity + 1):
            candidate_now = reduce_item(own_now, item, quantity)
            candidate_next = add_item(own_next, item, quantity)
            if candidate_next is None:
                continue
            cand_now_revenue, cand_inventory = simulate_item_market(
                module,
                start_inventory,
                [candidate_now, opp_now] if own_seat == 0 else [opp_now, candidate_now],
                [own_available_now, opp_available_now] if own_seat == 0 else [opp_available_now, own_available_now],
                item,
            )
            cand_inventory -= demand
            cand_next_revenue, _ = simulate_item_market(
                module,
                cand_inventory,
                [candidate_next, opp_next] if own_seat == 0 else [opp_next, candidate_next],
                [base_next_available + quantity, opp_next_available] if own_seat == 0 else [opp_next_available, base_next_available + quantity],
                item,
            )
            cand_own = cand_now_revenue[own_seat] + cand_next_revenue[own_seat]
            cand_opp = cand_now_revenue[other] + cand_next_revenue[other]
            own_delta = cand_own - base_own
            margin_delta = (cand_own - cand_opp) - (base_own - base_opp)
            key = (margin_delta, own_delta, -quantity)
            if own_delta >= config.min_predicted_gain and margin_delta > 0 and (best is None or key > best[0]):
                best = (key, quantity, margin_delta)
        if best is not None:
            result[item] = (best[1], best[2])
    return result


def apply_unit_queue(farm: dict, private: dict, action: dict, step: int) -> None:
    unit_actions = [action.get("farmer", ["PASS"]), *(action.get("hands") or [])]
    demand = {}
    for order in unit_actions:
        if isinstance(order, list) and len(order) >= 2 and order[0] == "PLANT":
            demand[order[1]] = demand.get(order[1], 0) + 1
    blocked = {item for item, count in demand.items() if count > private["seeds"].get(item, 0)}

    def allowed(order):
        if isinstance(order, list) and len(order) >= 2 and order[0] == "PLANT" and order[1] in blocked:
            return ["PASS"]
        return order

    day = step // 24
    RULES._apply_unit_action(farm, private, 0, allowed(unit_actions[0]), 10, day, 24, 100)
    for index, order in enumerate(unit_actions[1:], 1):
        RULES._apply_unit_action(farm, private, index, allowed(order), 10, day, 24, 100)


def advance_full_state(state: dict, actions: list[dict], step: int, seed: int) -> dict:
    result = copy.deepcopy(state)
    for seat in (0, 1):
        apply_unit_queue(result["farms"][seat], result["privates"][seat], actions[seat], step)
    shared = SimpleNamespace(
        farms=result["farms"], market=result["market"], town=result["town"], step=step
    )
    states = [
        SimpleNamespace(
            observation=SimpleNamespace(
                farms=shared.farms,
                market=shared.market,
                town=shared.town,
                private=result["privates"][seat],
            ),
            action=actions[seat],
        )
        for seat in (0, 1)
    ]
    env = SimpleNamespace(configuration=SimpleNamespace(), info={"seed": int(seed)})
    RULES._process_market(states, env)
    RULES._town_consume(env, states, step)
    for farm in result["farms"]:
        RULES._decay_plants(farm, step)
    if (step + 1) % 24 == 0:
        RULES._end_of_day(states, env, step // 24)
    return result


def state_from_observations(actual_obs: dict, opponent_obs: dict, own_seat: int) -> dict:
    privates = [None, None]
    privates[own_seat] = copy.deepcopy(actual_obs["private"])
    privates[1 - own_seat] = copy.deepcopy(opponent_obs["private"])
    return {
        "farms": copy.deepcopy(actual_obs["farms"]),
        "market": copy.deepcopy(actual_obs["market"]),
        "town": copy.deepcopy(actual_obs["town"]),
        "privates": privates,
    }


def state_equal_except_money(left: dict, right: dict) -> bool:
    left = copy.deepcopy(left)
    right = copy.deepcopy(right)
    for seat in (0, 1):
        left["farms"][seat].pop("money", None)
        right["farms"][seat].pop("money", None)
    return left == right


def full_oracle_decisions(
    module,
    actual_obs: dict,
    opponent_obs: dict,
    streams: list[list[dict]],
    step: int,
    own_seat: int,
    config: DelayConfig,
    seed: int,
) -> dict[str, tuple[int, int]]:
    if step + 1 >= len(streams[0]) or step % 4 != 0:
        return {}
    other = 1 - own_seat
    current_actions = [canonical_action(streams[seat][step]) for seat in (0, 1)]
    next_actions = [canonical_action(streams[seat][step + 1]) for seat in (0, 1)]
    initial = state_from_observations(actual_obs, opponent_obs, own_seat)
    baseline = advance_full_state(initial, current_actions, step, seed)
    baseline = advance_full_state(baseline, next_actions, step + 1, seed)
    base_own = float(baseline["farms"][own_seat]["money"])
    base_opp = float(baseline["farms"][other]["money"])
    own_action = current_actions[own_seat]
    available = {
        item: projected_available(module, actual_obs, own_action, item) for item in NON_WHEAT
    }
    best = None
    for item in config.target_items:
        requested = sum(
            max(0, int(order[2] or 0))
            for order in own_action["market"]
            if len(order) >= 3 and order[0] == "SELL" and order[1] == item
        )
        if requested <= 0 or module._v17_town_demand_at(actual_obs, item, step) <= 0:
            continue
        if module._v17_pickup_reserve(next_actions[own_seat], item) > 0:
            continue
        for quantity in range(1, min(requested, available[item], config.max_batch) + 1):
            candidate_current = copy.deepcopy(current_actions)
            candidate_next = copy.deepcopy(next_actions)
            candidate_current[own_seat] = reduce_item(candidate_current[own_seat], item, quantity)
            amended = add_item(candidate_next[own_seat], item, quantity)
            if amended is None:
                continue
            candidate_next[own_seat] = amended
            candidate = advance_full_state(initial, candidate_current, step, seed)
            candidate = advance_full_state(candidate, candidate_next, step + 1, seed)
            if not state_equal_except_money(candidate, baseline):
                continue
            own_delta = float(candidate["farms"][own_seat]["money"]) - base_own
            opp_delta = float(candidate["farms"][other]["money"]) - base_opp
            margin_delta = own_delta - opp_delta
            key = (margin_delta, own_delta, -quantity, item)
            if own_delta >= config.min_predicted_gain and margin_delta > 0 and (best is None or key > best[0]):
                best = (key, item, quantity, int(round(margin_delta)))
    return {} if best is None else {best[1]: (best[2], best[3])}


def run_frozen_candidate(
    seed: int,
    streams: list[list[dict]],
    baseline_observations: list[list[dict]],
    own_seat: int,
    config: DelayConfig,
    oracle_mode: str,
) -> tuple[tuple[float, float], dict, int]:
    module = load_a2(f"frozen_{seed}_{own_seat}")
    planner = DemandDelayPlanner(module, config)
    game = KAGSIM.Game(int(seed))
    production_mismatches = 0
    for step in range(len(streams[0])):
        before = game.observe(own_seat)
        baseline_action = copy.deepcopy(streams[own_seat][step])
        decisions = None
        if not planner.pending[own_seat] and oracle_mode == "queue":
            decisions = oracle_decisions(module, before, baseline_observations, streams, step, own_seat, config)
        elif not planner.pending[own_seat] and oracle_mode == "full":
            decisions = full_oracle_decisions(
                module,
                before,
                baseline_observations[1 - own_seat][step],
                streams,
                step,
                own_seat,
                config,
                seed,
            )
        candidate_action = planner.adapt(before, baseline_action, decisions)
        if candidate_action["farmer"] != baseline_action["farmer"] or candidate_action["hands"] != baseline_action["hands"]:
            production_mismatches += 1
        actions = [None, None]
        actions[own_seat] = candidate_action
        actions[1 - own_seat] = copy.deepcopy(streams[1 - own_seat][step])
        game.step(actions[0], actions[1])
    return (
        (float(game.reward(0)), float(game.reward(1))),
        planner.diagnostics(own_seat),
        production_mismatches,
    )


def run_live_candidate(seed: int, own_seat: int, config: DelayConfig) -> tuple[tuple[float, float], dict]:
    candidate_module = load_a2(f"live_candidate_{seed}_{own_seat}")
    opponent_module = load_a2(f"live_opponent_{seed}_{own_seat}")
    planner = DemandDelayPlanner(candidate_module, config)
    game = KAGSIM.Game(int(seed))
    while not game.done:
        actions = [None, None]
        actions[own_seat] = planner.act(game.observe(own_seat))
        actions[1 - own_seat] = opponent_module.agent(game.observe(1 - own_seat))
        game.step(actions[0], actions[1])
    return (float(game.reward(0)), float(game.reward(1))), planner.diagnostics(own_seat)


def summarize(rows: list[dict]) -> dict:
    own = [row["own_delta"] for row in rows]
    margin = [row["margin_delta"] for row in rows]
    return {
        "comparisons": len(rows),
        "own_positive_zero_negative": [sum(x > 0 for x in own), sum(x == 0 for x in own), sum(x < 0 for x in own)],
        "own_delta_mean": statistics.mean(own),
        "own_delta_median": statistics.median(own),
        "own_delta_min": min(own),
        "own_delta_max": max(own),
        "margin_positive_zero_negative": [sum(x > 0 for x in margin), sum(x == 0 for x in margin), sum(x < 0 for x in margin)],
        "margin_delta_mean": statistics.mean(margin),
        "delay_steps": sum(row["diagnostics"].get("delay_steps", 0) for row in rows),
        "delayed_units": sum(row["diagnostics"].get("delayed_units", 0) for row in rows),
        "unwound_units": sum(row["diagnostics"].get("unwound_units", 0) for row in rows),
        "unwind_shortfall_units": sum(row["diagnostics"].get("unwind_shortfall_units", 0) for row in rows),
        "predicted_gain": sum(row["diagnostics"].get("predicted_gain", 0) for row in rows),
        "production_action_mismatches": sum(row.get("production_action_mismatches", 0) for row in rows),
    }


def evaluate(seed_count: int, config: DelayConfig, mode: str, oracle_mode: str) -> dict:
    frozen_rows = []
    live_rows = []
    identity_failures = 0
    for seed in range(seed_count):
        streams, observations, baseline = capture_live_a2(seed)
        if replay_streams(seed, streams) != baseline:
            identity_failures += 1
            continue
        for seat in (0, 1):
            other = 1 - seat
            if mode in ("both", "frozen"):
                candidate, diagnostics, mismatches = run_frozen_candidate(
                    seed, streams, observations, seat, config, oracle_mode
                )
                frozen_rows.append({
                    "seed": seed,
                    "seat": seat,
                    "own_delta": candidate[seat] - baseline[seat],
                    "opponent_delta": candidate[other] - baseline[other],
                    "margin_delta": (candidate[seat] - candidate[other]) - (baseline[seat] - baseline[other]),
                    "diagnostics": diagnostics,
                    "production_action_mismatches": mismatches,
                })
            if mode in ("both", "live"):
                candidate, diagnostics = run_live_candidate(seed, seat, config)
                live_rows.append({
                    "seed": seed,
                    "seat": seat,
                    "own_delta": candidate[seat] - baseline[seat],
                    "opponent_delta": candidate[other] - baseline[other],
                    "margin_delta": (candidate[seat] - candidate[other]) - (baseline[seat] - baseline[other]),
                    "diagnostics": diagnostics,
                })
    result = {
        "status": "RESEARCH_PILOT_NOT_SUBMISSION_QUALIFIED",
        "cppsim_engine": KAGSIM.ENGINE_VERSION,
        "config": config.__dict__,
        "seed_count": seed_count,
        "identity_failures": identity_failures,
        "frozen_oracle": oracle_mode,
    }
    if frozen_rows:
        result["frozen"] = {"summary": summarize(frozen_rows), "rows": frozen_rows}
    if live_rows:
        result["live"] = {"summary": summarize(live_rows), "rows": live_rows}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--mode", choices=("both", "frozen", "live"), default="both")
    parser.add_argument("--fraction", type=float, default=1.0)
    parser.add_argument("--max-batch", type=int, default=30)
    parser.add_argument("--min-gain", type=int, default=2)
    parser.add_argument("--cash-floor", type=int, default=5000)
    parser.add_argument("--shed-cap", type=int, default=96)
    parser.add_argument("--opponent-buffer", type=float, default=0.0)
    parser.add_argument("--oracle", choices=("none", "queue", "full"), default="none")
    parser.add_argument("--items", default="STRAWBERRY,MILK,WOOL")
    parser.add_argument("--sell-only-window", action="store_true")
    args = parser.parse_args()
    config = DelayConfig(
        fraction=args.fraction,
        max_batch=args.max_batch,
        min_predicted_gain=args.min_gain,
        cash_floor=args.cash_floor,
        shed_soft_cap=args.shed_cap,
        opponent_buffer_multiplier=args.opponent_buffer,
        target_items=tuple(item.strip().upper() for item in args.items.split(",") if item.strip()),
        require_sell_only_window=args.sell_only_window,
    )
    if args.oracle != "none" and args.mode == "live":
        parser.error("--oracle is only defined for frozen or both mode")
    print(json.dumps(evaluate(args.seeds, config, args.mode, args.oracle), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
