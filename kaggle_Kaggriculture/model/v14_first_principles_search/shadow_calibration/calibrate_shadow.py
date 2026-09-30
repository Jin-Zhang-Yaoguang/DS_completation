"""Calibrate deployable A2 opponent shadows on *already exposed* panels only.

The script replays the exact strict-oracle trajectories that already exist for
V13 screen36 and confirm100.  It never opens a new panel or a test split.  At
each turn three independent A2 shadows are called from step zero:

* A / own_private_copy: flip the seat and copy the candidate's current private.
* B / flow_corrected: advance an estimated private with the official engine,
  then correct product shed counts using the next observable market-inventory
  residual.
* C / forward_model: start from the public zero-private initial condition and
  advance only with predicted actions plus the public/current game state.

True opponent action/private is read only after every prediction has been
frozen and is used solely as an offline label.  Gate features are restricted
to information available before action submission: own planned action,
current public state, shadow predictions, and previous public transition
residuals.  Final reward/outcome is not written to the opportunity table and
is never used for gate selection.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Any, Mapping, Sequence

import numpy as np
from kaggle_environments.envs.kaggriculture import kaggriculture as kg


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

V10 = WORKSPACE / "kaggle_Kaggriculture/model/v10_replay_lolo_router"
ORACLE = WORKSPACE / "kaggle_Kaggriculture/model/v14_first_principles_search/oracle"
for path in (V10, ORACLE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agent_factory import create_agent, load_registry  # noqa: E402
from run_exposed_queue_oracle import (  # noqa: E402
    _all_sell,
    _branch,
    _canonical_action,
    _has_transfer,
)


A2 = "v12a2_no_shop_gate"
V13C = "v13c_a2_v8_no_wool_throttle"
PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
PRIVATE_SHED_ITEMS = PRODUCTS + ("GOOSE", "COW", "SHEEP")
SEEDS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
METHODS = ("A", "B", "C")


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return dict(value or {})


def _private(obs: Any) -> dict[str, Any]:
    raw = _as_dict(_as_dict(obs).get("private", {}))
    shed = _as_dict(raw.get("shed", {}))
    seeds = _as_dict(raw.get("seeds", {}))
    inventories = [_as_dict(value) for value in list(raw.get("inventories", []) or [])]
    return {
        "shed": {item: max(0, int(shed.get(item, 0) or 0)) for item in PRIVATE_SHED_ITEMS},
        "seeds": {item: max(0, int(seeds.get(item, 0) or 0)) for item in SEEDS},
        "inventories": inventories or [{}],
    }


def _zero_private() -> dict[str, Any]:
    return {
        "shed": {item: 0 for item in PRIVATE_SHED_ITEMS},
        "seeds": {item: 0 for item in SEEDS},
        "inventories": [{}],
    }


def _seat(obs: Any) -> int:
    return 1 if int(_as_dict(obs).get("player", 0) or 0) == 1 else 0


def _shadow_obs(candidate_obs: Any, private: Mapping[str, Any]) -> Any:
    result = copy.deepcopy(candidate_obs)
    result["player"] = 1 - _seat(candidate_obs)
    result["private"] = copy.deepcopy(dict(private))
    return result


def _market_inventory(obs: Any) -> dict[str, int]:
    market = _as_dict(_as_dict(obs).get("market", {}))
    inventory = _as_dict(market.get("inventory", {}))
    return {item: int(inventory.get(item, 0) or 0) for item in PRODUCTS}


def _farm_public(obs: Any, seat: int, *, include_money: bool = True) -> str:
    farm = _as_dict(list(_as_dict(obs).get("farms", []) or [])[seat])
    payload = {
        "farmer": list(farm.get("farmer", []) or []),
        "hands": [list(value) for value in list(farm.get("hands", []) or [])],
        "unlocked_quadrants": list(farm.get("unlocked_quadrants", []) or []),
        "hires_today": int(farm.get("hires_today", 0) or 0),
        "tiles": farm.get("tiles", []) or [],
    }
    if include_money:
        payload["money"] = float(farm.get("money", 0.0) or 0.0)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _public_equal(obs: Any) -> bool:
    farms = list(_as_dict(obs).get("farms", []) or [])
    return len(farms) == 2 and _farm_public(obs, 0, include_money=False) == _farm_public(obs, 1, include_money=False)


def _clone_distance(obs: Any) -> int:
    farms = list(_as_dict(obs).get("farms", []) or [])
    if len(farms) != 2:
        return 10**9
    left = _as_dict(farms[0])
    right = _as_dict(farms[1])
    distance = abs(len(left.get("hands", []) or []) - len(right.get("hands", []) or []))
    distance += 3 * abs(
        len(left.get("unlocked_quadrants", []) or [])
        - len(right.get("unlocked_quadrants", []) or [])
    )
    lt = json.dumps(left.get("tiles", []), sort_keys=True, separators=(",", ":"))
    rt = json.dumps(right.get("tiles", []), sort_keys=True, separators=(",", ":"))
    if lt != rt:
        # Exact tile-cell mismatch count is more interpretable than edit distance.
        for lrow, rrow in zip(left.get("tiles", []) or [], right.get("tiles", []) or []):
            for ltile, rtile in zip(lrow, rrow):
                if ltile != rtile:
                    distance += 1
    return int(distance)


def _market_counter(action: Mapping[str, Any]) -> Counter[tuple[Any, ...]]:
    return Counter(tuple(order) for order in action.get("market", []) or [])


def _sell_qty(action: Mapping[str, Any]) -> Counter[str]:
    result: Counter[str] = Counter()
    for order in action.get("market", []) or []:
        if len(order) >= 3 and str(order[0]) == "SELL" and str(order[1]) in PRODUCTS:
            result[str(order[1])] += max(0, int(order[2] or 0))
    return result


def _candidate_opportunity(action: Mapping[str, Any], step: int, max_orders: int = 7) -> bool:
    market = list(action.get("market", []) or [])
    return (
        int(step) >= 96
        and _all_sell(action)
        and 2 <= len(market) <= int(max_orders)
        and len({str(order[1]) for order in market}) >= 2
        and not _has_transfer(action)
    )


def _align_inventories(private: dict[str, Any], obs: Any, seat: int) -> dict[str, Any]:
    result = copy.deepcopy(private)
    farms = list(_as_dict(obs).get("farms", []) or [])
    target = 1 + len(_as_dict(farms[seat]).get("hands", []) or []) if len(farms) == 2 else 1
    inventories = list(result.get("inventories", []) or [])
    while len(inventories) < target:
        inventories.append({})
    result["inventories"] = inventories[:target]
    return result


def _step_private_model(
    env: Any,
    candidate_seat: int,
    estimated_private: Mapping[str, Any],
    candidate_action: Mapping[str, Any],
    shadow_action: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, int], str, float]:
    """Advance a private estimate with official transition primitives.

    Deep-copying a complete Kaggle environment three times per turn makes the
    calibration prohibitively slow.  This function copies only the public
    farms/market/town plus two private payloads, then calls the same private
    unit/market/day primitives as the official interpreter.
    """

    opponent_seat = 1 - candidate_seat
    obs = env.state[candidate_seat].observation
    payload = _as_dict(obs)
    farms = copy.deepcopy(list(payload.get("farms", []) or []))
    market = copy.deepcopy(_as_dict(payload.get("market", {})))
    town = copy.deepcopy(_as_dict(payload.get("town", {})))
    privates = [_zero_private(), _zero_private()]
    privates[candidate_seat] = _private(obs)
    privates[opponent_seat] = _align_inventories(
        copy.deepcopy(dict(estimated_private)), obs, opponent_seat
    )
    actions = [candidate_action, shadow_action] if candidate_seat == 0 else [shadow_action, candidate_action]
    cfg = env.configuration
    board_size = int(kg.get(cfg, "boardSize", 10))
    turns_per_day = max(1, int(kg.get(cfg, "turnsPerDay", 24)))
    shed_capacity = int(kg.get(cfg, "shedCapacity", 100))
    max_orders = max(1, int(kg.get(cfg, "maxMarketOrdersPerTurn", 10)))
    hire_mult = int(kg.get(cfg, "farmHandCostMult", kg.FARM_HAND_COST_MULT))
    step = int(payload.get("step", 0) or 0)
    day = step // turns_per_day

    for player_id, action in enumerate(actions):
        action = _canonical_action(action)
        unit_actions = [action["farmer"], *action["hands"]]
        plant_demand: Counter[str] = Counter()
        for unit_action in unit_actions:
            if len(unit_action) >= 2 and str(unit_action[0]) == "PLANT":
                plant_demand[str(unit_action[1])] += 1
        blocked = {
            crop for crop, count in plant_demand.items()
            if count > int(privates[player_id]["seeds"].get(crop, 0) or 0)
        }
        for actor, unit_action in enumerate(unit_actions):
            allowed = (
                ["PASS"]
                if len(unit_action) >= 2
                and str(unit_action[0]) == "PLANT"
                and str(unit_action[1]) in blocked
                else unit_action
            )
            kg._apply_unit_action(
                farms[player_id], privates[player_id], actor, allowed,
                board_size, day, turns_per_day, shed_capacity,
            )

    queues = [list(_canonical_action(action)["market"])[:max_orders] for action in actions]
    for index in range(max((len(queue) for queue in queues), default=0)):
        order_states = [
            kg._parse_order(queue[index]) if index < len(queue) else None
            for queue in queues
        ]
        for player_id, order_state in enumerate(order_states):
            if order_state is None:
                continue
            if order_state["type"] == "HIRE":
                kg._do_hire(farms[player_id], privates[player_id], board_size, hire_mult)
                order_states[player_id] = None
            elif order_state["type"] == "BUY_LAND":
                kg._do_buy_land(farms[player_id], board_size)
                order_states[player_id] = None
        while True:
            quoted = [None, None]
            for player_id, order_state in enumerate(order_states):
                if order_state is None or order_state["remaining"] <= 0:
                    continue
                op = order_state["type"]
                item = order_state["item"]
                if op == "SELL" and item in kg.PRODUCTS:
                    quoted[player_id] = (
                        op, item, kg.market_price(item, market["inventory"][item], market.get("params")), order_state
                    )
                elif op == "BUY_PRODUCT" and item in ("WHEAT", "FERTILIZER"):
                    quoted[player_id] = (
                        op, item, kg.market_price(item, market["inventory"][item] - 1, market.get("params")), order_state
                    )
                elif op == "BUY_SEED" and item in kg.CROPS:
                    quoted[player_id] = (op, item, kg.CROPS[item]["seed"], order_state)
                elif op == "BUY_ANIMAL" and item in kg.ANIMALS:
                    quoted[player_id] = (op, item, kg.ANIMALS[item]["cost"], order_state)
                else:
                    order_states[player_id] = None
            if all(value is None for value in quoted):
                break
            committed_any = False
            for player_id, quote in enumerate(quoted):
                if quote is None:
                    continue
                op, item, price, order_state = quote
                committed = kg._commit_unit(
                    op, item, price, farms[player_id], privates[player_id], market, shed_capacity
                )
                if committed:
                    order_state["remaining"] -= 1
                    committed_any = True
                else:
                    order_states[player_id] = None
            if not committed_any:
                break
        kg._refresh_prices(market)

    shop_interval = max(1, int(kg.get(cfg, "townShopSellInterval", 4)))
    center_interval = max(1, int(kg.get(cfg, "townCenterSellInterval", 24)))
    if step % shop_interval == 0:
        for shop_name in town.get("unlocked_shops", []):
            products = kg.SHOPS[shop_name]
            multiplier = 2 if len(products) == 1 else 1
            for item in products:
                market["inventory"][item] -= multiplier
    if step % center_interval == 0:
        for item in kg.TOWN_CENTER_PRODUCTS:
            market["inventory"][item] -= 1
    kg._refresh_prices(market)
    for farm in farms:
        kg._decay_plants(farm, step)
    if (step + 1) % turns_per_day == 0:
        weed_chance = float(kg.get(cfg, "weedSpawnChance", 0.005))
        rng = random.Random((int(env.info.get("seed", 0)) * 1_000_003) ^ day)
        for player_id, farm in enumerate(farms):
            kg._daily_refresh_plants(farm, day, turns_per_day)
            kg._daily_refresh_animals(farm, day)
            kg._spawn_weeds(farm, board_size, weed_chance, rng)
            kg._drop_inventories_to_shed(privates[player_id], shed_capacity)
            farm["farmer"] = list(kg._default_spawn(board_size))
            farm["hands"] = []
            farm["hires_today"] = 0
            privates[player_id]["inventories"] = [{}]

    money = float(farms[opponent_seat].get("money", 0.0) or 0.0)
    predicted_obs = {
        "farms": farms,
        "market": market,
        "private": privates[opponent_seat],
    }
    return (
        _private(predicted_obs),
        {item: int(market["inventory"].get(item, 0) or 0) for item in PRODUCTS},
        _farm_public(predicted_obs, opponent_seat, include_money=False),
        money,
    )


def _flow_correct(
    predicted_private: Mapping[str, Any],
    predicted_market: Mapping[str, int],
    actual_market: Mapping[str, int],
) -> tuple[dict[str, Any], dict[str, int], int]:
    """Assign observable shared-market residuals to the opponent product shed.

    If actual market inventory is +d above the predicted market, the opponent
    made d more net sales than predicted, so its post-turn shed point estimate
    is reduced by d.  The reverse holds for net buys.  The correction cannot
    see a sale executed at the $1 price floor because that sale does not change
    public market inventory; such turns are flagged separately by the caller.
    """

    result = copy.deepcopy(dict(predicted_private))
    shed = {item: int(_as_dict(result.get("shed", {})).get(item, 0) or 0) for item in PRIVATE_SHED_ITEMS}
    residual = {
        item: int(actual_market.get(item, 0)) - int(predicted_market.get(item, 0))
        for item in PRODUCTS
    }
    for item, delta in residual.items():
        shed[item] = max(0, shed[item] - delta)
    overflow = max(0, sum(shed.values()) - 100)
    # A point estimator must respect the engine capacity.  Trim deterministic
    # largest product estimates only if correction noise makes it impossible.
    if overflow:
        for item in sorted(PRIVATE_SHED_ITEMS, key=lambda key: (shed[key], key), reverse=True):
            take = min(overflow, shed[item])
            shed[item] -= take
            overflow -= take
            if not overflow:
                break
    result["shed"] = shed
    return result, residual, sum(abs(value) for value in residual.values())


def _method_label(
    predicted: Mapping[str, Any],
    estimated_private: Mapping[str, Any],
    actual: Mapping[str, Any],
    true_private: Mapping[str, Any],
) -> dict[str, Any]:
    predicted = _canonical_action(predicted)
    actual = _canonical_action(actual)
    estimated_shed = _as_dict(estimated_private.get("shed", {}))
    true_shed = _as_dict(true_private.get("shed", {}))
    predicted_qty = _sell_qty(predicted)
    actual_qty = _sell_qty(actual)
    cap_exact = True
    sufficient = True
    for item in PRODUCTS:
        requested = int(actual_qty[item])
        true_cap = min(requested, int(true_shed.get(item, 0) or 0))
        estimated_cap = min(requested, int(estimated_shed.get(item, 0) or 0))
        cap_exact = cap_exact and true_cap == estimated_cap
        sufficient = sufficient and int(estimated_shed.get(item, 0) or 0) >= true_cap
    per_product_abs_error = {
        item: abs(int(predicted_qty[item]) - int(actual_qty[item])) for item in PRODUCTS
    }
    shed_abs_error = {
        item: abs(int(estimated_shed.get(item, 0) or 0) - int(true_shed.get(item, 0) or 0))
        for item in PRODUCTS
    }
    return {
        "queue_exact": predicted["market"] == actual["market"],
        "market_multiset_exact": _market_counter(predicted) == _market_counter(actual),
        "sell_qty_exact": predicted_qty == actual_qty,
        "production_exact": (
            predicted["farmer"] == actual["farmer"]
            and predicted["hands"] == actual["hands"]
        ),
        "actual_all_sell": _all_sell(actual),
        "actual_has_transfer": _has_transfer(actual),
        "shed_exact": all(value == 0 for value in shed_abs_error.values()),
        "shed_l1": sum(shed_abs_error.values()),
        "actual_queue_exec_cap_exact": cap_exact,
        "shed_sufficient_for_actual_exec": sufficient,
        "per_product_qty_abs_error": per_product_abs_error,
        "per_product_shed_abs_error": shed_abs_error,
    }


def _run_game(task: Mapping[str, Any]) -> dict[str, Any]:
    from kaggle_environments import make

    registry = load_registry(task["registry"])
    candidate_id = str(task["candidate"])
    candidate = create_agent(registry, candidate_id)
    opponent = create_agent(registry, A2)
    shadows = {method: create_agent(registry, A2) for method in METHODS}
    seat = int(task["candidate_seat"])
    other = 1 - seat
    source = dict(task["source"])
    seed = int(source["seed"])
    random.seed(seed * 104729 + seat * 1009)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.reset(2)
    estimates = {"B": _zero_private(), "C": _zero_private()}
    history = {
        method: {
            "market_residual_l1": 0,
            "public_transition_match": True,
            "money_error": 0.0,
            "observable_streak": 0,
            "observable_mismatches": 0,
        }
        for method in METHODS
    }
    opportunities: list[dict[str, Any]] = []
    eligible_steps = 0
    triggered_steps = 0
    step = 0
    while [str(state.status) for state in env.state] == ["ACTIVE", "ACTIVE"]:
        for state in env.state:
            state.observation.step = step
        candidate_obs = env.state[seat].observation
        opponent_obs = env.state[other].observation
        own_private = _private(candidate_obs)
        true_private = _private(opponent_obs)
        candidate_action = _canonical_action(candidate(candidate_obs, env.configuration))
        actual_opponent_action = _canonical_action(opponent(opponent_obs, env.configuration))
        private_inputs = {
            "A": own_private,
            "B": _align_inventories(estimates["B"], candidate_obs, other),
            "C": _align_inventories(estimates["C"], candidate_obs, other),
        }
        shadow_actions = {
            method: _canonical_action(
                shadows[method](_shadow_obs(candidate_obs, private_inputs[method]), env.configuration)
            )
            for method in METHODS
        }
        candidate_branch = _branch(candidate)
        actual_branch = _branch(opponent)
        shadow_branches = {method: _branch(shadows[method]) for method in METHODS}
        public_equal = _public_equal(candidate_obs)
        clone_distance = _clone_distance(candidate_obs)
        consensus_queue = len({json.dumps(shadow_actions[m]["market"], sort_keys=True) for m in METHODS}) == 1
        consensus_full = len({json.dumps(shadow_actions[m], sort_keys=True) for m in METHODS}) == 1

        observable: dict[str, dict[str, Any]] = {}
        for method in METHODS:
            predicted = shadow_actions[method]
            production_match_own = (
                candidate_action["farmer"] == predicted["farmer"]
                and candidate_action["hands"] == predicted["hands"]
            )
            multiset_match_own = _market_counter(candidate_action) == _market_counter(predicted)
            full_match_own = candidate_action == predicted
            branch_match_own = bool(candidate_branch) and candidate_branch == shadow_branches[method]
            conforms_now = (
                public_equal
                and production_match_own
                and multiset_match_own
                and branch_match_own
                and int(history[method]["market_residual_l1"]) == 0
                and bool(history[method]["public_transition_match"])
            )
            if conforms_now:
                history[method]["observable_streak"] += 1
            else:
                history[method]["observable_streak"] = 0
                history[method]["observable_mismatches"] += 1
            observable[method] = {
                "shadow_all_sell": _all_sell(predicted),
                "shadow_has_transfer": _has_transfer(predicted),
                "production_match_own": production_match_own,
                "market_multiset_match_own": multiset_match_own,
                "full_action_match_own": full_match_own,
                "branch_match_own": branch_match_own,
                "previous_market_residual_l1": int(history[method]["market_residual_l1"]),
                "previous_public_transition_match": bool(history[method]["public_transition_match"]),
                "previous_money_error": float(history[method]["money_error"]),
                "observable_streak": int(history[method]["observable_streak"]),
                "observable_mismatches": int(history[method]["observable_mismatches"]),
            }

        is_opportunity = _candidate_opportunity(candidate_action, step, int(task["max_orders"]))
        if is_opportunity:
            row: dict[str, Any] = {
                "schema": "kaggriculture-v14-shadow-opportunity-1",
                "panel": str(task["panel_name"]),
                "candidate": candidate_id,
                "candidate_seat": seat,
                "source": source,
                "step": step,
                "day": int(_as_dict(candidate_obs).get("day", 0) or 0),
                "hour": int(_as_dict(candidate_obs).get("hour", 0) or 0),
                "candidate_branch": candidate_branch,
                "actual_opponent_branch": actual_branch,
                "public_production_equal": public_equal,
                "clone_distance": clone_distance,
                "candidate_queue": candidate_action["market"],
                "actual_opponent_queue": actual_opponent_action["market"],
                "abc_queue_consensus": consensus_queue,
                "abc_full_action_consensus": consensus_full,
                "methods": {},
            }
            for method in METHODS:
                labels = _method_label(
                    shadow_actions[method], private_inputs[method], actual_opponent_action, true_private
                )
                row["methods"][method] = {
                    "name": {
                        "A": "own_private_copy",
                        "B": "flow_corrected",
                        "C": "forward_model",
                    }[method],
                    "shadow_branch": shadow_branches[method],
                    "predicted_queue": shadow_actions[method]["market"],
                    "estimated_product_shed": {
                        item: int(_as_dict(private_inputs[method].get("shed", {})).get(item, 0) or 0)
                        for item in PRODUCTS
                    },
                    "observable": observable[method],
                    "label": labels,
                }
            opportunities.append(row)

        # Reapply the already-recorded oracle intervention instead of searching
        # the same factorial permutation space again.  Events in the sealed
        # oracle log contain only triggered changes; every absent step keeps the
        # parent queue.  This both guarantees trajectory identity and prevents
        # the calibration from becoming a second oracle experiment.
        chosen = copy.deepcopy(candidate_action)
        logged_queue = task["evidence"]["chosen_by_step"].get(str(step))
        if logged_queue is not None:
            chosen["market"] = copy.deepcopy(logged_queue)
            triggered_steps += 1

        predictions = {}
        for method in METHODS:
            predictions[method] = _step_private_model(
                env,
                seat,
                private_inputs[method],
                chosen,
                shadow_actions[method],
            )
        actions = [chosen, actual_opponent_action] if seat == 0 else [actual_opponent_action, chosen]
        env.step(actions)
        if [str(state.status) for state in env.state] == ["ACTIVE", "ACTIVE"]:
            actual_next_obs = env.state[other].observation
            actual_market = _market_inventory(actual_next_obs)
            actual_public = _farm_public(actual_next_obs, other, include_money=False)
            farms = list(_as_dict(actual_next_obs).get("farms", []) or [])
            actual_money = float(_as_dict(farms[other]).get("money", 0.0) or 0.0)
            for method in METHODS:
                next_private, predicted_market, predicted_public, predicted_money = predictions[method]
                residual = {
                    item: int(actual_market[item]) - int(predicted_market[item]) for item in PRODUCTS
                }
                history[method]["market_residual_l1"] = sum(abs(value) for value in residual.values())
                history[method]["public_transition_match"] = predicted_public == actual_public
                history[method]["money_error"] = float(predicted_money - actual_money)
                if method == "B":
                    estimates["B"], _, _ = _flow_correct(next_private, predicted_market, actual_market)
                elif method == "C":
                    estimates["C"] = next_private
        step += 1
        if step > 1000:
            raise RuntimeError("environment exceeded 1000 steps")

    rewards = [float(state.reward or 0.0) for state in env.state]
    margin = rewards[seat] - rewards[other]
    evidence = dict(task["evidence"])
    eligible_steps = int(evidence.get("eligible_steps", -1))
    replay_match = (
        int(evidence.get("triggered_steps", -1)) == triggered_steps
        and int(evidence.get("eligible_steps", -1)) == eligible_steps
        and abs(float(evidence.get("margin", math.nan)) - margin) <= 1e-9
    )
    return {
        "panel": str(task["panel_name"]),
        "candidate": candidate_id,
        "candidate_seat": seat,
        "source": source,
        "opportunities": opportunities,
        "opportunity_count": len(opportunities),
        "eligible_steps": eligible_steps,
        "triggered_steps": triggered_steps,
        "replay_match": replay_match,
        "evidence_key": [seed, seat],
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _evidence_map(path: Path) -> dict[tuple[int, int], dict[str, Any]]:
    result = {}
    for row in _read_jsonl(path):
        key = (int(row["source"]["seed"]), int(row["candidate_seat"]))
        result[key] = {
            "eligible_steps": int(row["eligible_steps"]),
            "triggered_steps": int(row["triggered_steps"]),
            "margin": float(row["margin"]),
            "chosen_by_step": {
                str(int(event["step"])): copy.deepcopy(event["chosen_queue"])
                for event in list(row.get("events") or [])
                if bool(event.get("triggered"))
            },
        }
    return result


def _gate_selected(row: Mapping[str, Any], method: str, gate: str) -> bool:
    payload = row["methods"][method]
    obs = payload["observable"]
    if not obs["shadow_all_sell"] or obs["shadow_has_transfer"]:
        return False
    if gate == "base":
        return True
    flow_history = (
        int(obs["previous_market_residual_l1"]) == 0
        and bool(obs["previous_public_transition_match"])
        and abs(float(obs["previous_money_error"])) <= 1e-9
    )
    if gate == "flow_history":
        return flow_history
    own_shadow = (
        flow_history
        and obs["production_match_own"]
        and obs["market_multiset_match_own"]
        and obs["branch_match_own"]
    )
    if gate == "own_shadow":
        return own_shadow
    if gate == "history_consensus":
        return flow_history and bool(row["abc_queue_consensus"])
    mirror = (
        bool(row["public_production_equal"])
        and int(row["clone_distance"]) == 0
        and own_shadow
    )
    if gate == "mirror_now":
        return mirror
    history = mirror
    if gate == "history_exact":
        return history
    consensus = history and bool(row["abc_queue_consensus"])
    if gate == "abc_consensus":
        return consensus
    if gate.startswith("streak_"):
        threshold = int(gate.split("_", 1)[1])
        return consensus and int(obs["observable_streak"]) >= threshold
    raise KeyError(gate)


def _wilson_lower(successes: int, total: int, z: float = 1.959963984540054) -> float:
    if total <= 0:
        return 0.0
    p = successes / total
    denominator = 1.0 + z * z / total
    centre = p + z * z / (2.0 * total)
    spread = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total)
    return (centre - spread) / denominator


def _metric_block(rows: Sequence[Mapping[str, Any]], method: str) -> dict[str, Any]:
    n = len(rows)
    labels = [row["methods"][method]["label"] for row in rows]
    result: dict[str, Any] = {"opportunities": n}
    for key in (
        "queue_exact", "market_multiset_exact", "sell_qty_exact", "production_exact",
        "shed_exact", "actual_queue_exec_cap_exact", "shed_sufficient_for_actual_exec",
    ):
        count = sum(bool(label[key]) for label in labels)
        result[key] = {
            "count": count,
            "rate": count / n if n else None,
            "wilson95_lower": _wilson_lower(count, n) if n else None,
        }
    result["shed_l1_mean"] = sum(float(label["shed_l1"]) for label in labels) / n if n else None
    result["per_product"] = {}
    for item in PRODUCTS:
        qty_errors = [int(label["per_product_qty_abs_error"][item]) for label in labels]
        shed_errors = [int(label["per_product_shed_abs_error"][item]) for label in labels]
        result["per_product"][item] = {
            "sell_qty_exact_rate": sum(value == 0 for value in qty_errors) / n if n else None,
            "sell_qty_mae": sum(qty_errors) / n if n else None,
            "shed_exact_rate": sum(value == 0 for value in shed_errors) / n if n else None,
            "shed_mae": sum(shed_errors) / n if n else None,
        }
    return result


def _group_metrics(rows: Sequence[Mapping[str, Any]], method: str, key_fn: Any) -> dict[str, Any]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(key_fn(row))].append(row)
    return {key: _metric_block(values, method) for key, values in sorted(groups.items())}


def _summarise(rows: list[dict[str, Any]], games: list[dict[str, Any]]) -> dict[str, Any]:
    gates = [
        "base", "flow_history", "history_consensus", "own_shadow",
        "mirror_now", "history_exact", "abc_consensus",
    ] + [
        f"streak_{value}" for value in (1, 4, 12, 24, 48, 96)
    ]
    summary: dict[str, Any] = {
        "schema": "kaggriculture-v14-shadow-calibration-summary-1",
        "epistemic_status": (
            "offline action/private-label calibration on already exposed V13 screen36/confirm100; "
            "not unseen validation and no final outcome used for gate fitting"
        ),
        "games": len(games),
        "opportunities": len(rows),
        "panels": dict(Counter(str(row["panel"]) for row in rows)),
        "replay_matches": sum(bool(game["replay_match"]) for game in games),
        "all_replays_match_existing_oracle": all(bool(game["replay_match"]) for game in games),
        "methods": {},
        "coverage_precision": {},
        "gate_feature_contract": {
            "base": "current shadow queue is nonempty SELL-only and has no worker shed transfer",
            "flow_history": "base plus previous predicted-vs-public market inventory, opponent farm and money residuals are exactly zero",
            "history_consensus": "flow_history plus A/B/C current predicted queues agree",
            "own_shadow": "flow_history plus current own-vs-shadow production action, market multiset and selected branch agree",
            "mirror_now": "own_shadow plus current public production states are byte-equal and clone_distance is zero",
            "history_exact": "alias of mirror_now retained for the original calibration curve",
            "abc_consensus": "mirror_now plus A/B/C current predicted queues agree",
            "streak_N": "abc_consensus plus at least N consecutive observable conformance turns",
            "forbidden_features": [
                "actual opponent current action", "actual opponent private", "final margin", "final outcome"
            ],
        },
    }
    for method in METHODS:
        summary["methods"][method] = {
            "name": {"A": "own_private_copy", "B": "flow_corrected", "C": "forward_model"}[method],
            "overall": _metric_block(rows, method),
            "by_panel": _group_metrics(rows, method, lambda row: row["panel"]),
            "by_date": _group_metrics(rows, method, lambda row: row["source"]["date"]),
            "by_seat": _group_metrics(rows, method, lambda row: row["candidate_seat"]),
            "by_branch": _group_metrics(
                rows,
                method,
                lambda row: f"{row.get('candidate_branch') or 'unknown'}/{row.get('actual_opponent_branch') or 'unknown'}",
            ),
        }
        curve = []
        for gate in gates:
            selected = [row for row in rows if _gate_selected(row, method, gate)]
            exact = sum(bool(row["methods"][method]["label"]["queue_exact"]) for row in selected)
            multiset = sum(bool(row["methods"][method]["label"]["market_multiset_exact"]) for row in selected)
            qty = sum(bool(row["methods"][method]["label"]["sell_qty_exact"]) for row in selected)
            cap = sum(bool(row["methods"][method]["label"]["actual_queue_exec_cap_exact"]) for row in selected)
            curve.append({
                "gate": gate,
                "selected": len(selected),
                "coverage": len(selected) / len(rows) if rows else 0.0,
                "queue_exact": exact,
                "queue_false_positive": len(selected) - exact,
                "queue_precision": exact / len(selected) if selected else None,
                "queue_wilson95_lower": _wilson_lower(exact, len(selected)) if selected else None,
                "multiset_precision": multiset / len(selected) if selected else None,
                "sell_qty_precision": qty / len(selected) if selected else None,
                "exec_cap_precision": cap / len(selected) if selected else None,
            })
        summary["coverage_precision"][method] = curve

    candidates = []
    for method in METHODS:
        for row in summary["coverage_precision"][method]:
            if row["gate"] != "base" and row["selected"] and row["queue_false_positive"] == 0:
                candidates.append((row["selected"], method, row["gate"], row))
    if candidates:
        _, method, gate, selected = max(candidates, key=lambda value: (value[0], value[1] == "B", value[2]))
        summary["recommended_preregistered_gate"] = {
            "method": method,
            "gate": gate,
            "selection_rule": (
                "largest-coverage zero-observed-queue-error conformance gate on exposed calibration only; "
                "ties prefer B flow correction; no reward/outcome criterion"
            ),
            **selected,
        }
    else:
        summary["recommended_preregistered_gate"] = None
    return summary


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--max-orders", type=int, default=7)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--panel", choices=("screen36", "confirm100", "both"), default="both")
    parser.add_argument(
        "--registry",
        type=Path,
        default=WORKSPACE / "kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol/clean_screen_registry.json",
    )
    parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args()

    protocol = WORKSPACE / "kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol"
    oracle = WORKSPACE / "kaggle_Kaggriculture/model/v14_first_principles_search/oracle"
    specs = []
    if args.panel in {"screen36", "both"}:
        specs.append((
            "screen36_a2_parent_oracle",
            A2,
            protocol / "screen_panel.json",
            oracle / "a2_parent_oracle_games.jsonl",
            36,
        ))
    if args.panel in {"confirm100", "both"}:
        specs.append((
            "confirm100_v13c_parent_oracle",
            V13C,
            protocol / "confirmatory_panel.json",
            oracle / "strict_games.jsonl",
            100,
        ))
    tasks = []
    for panel_name, candidate_id, panel_path, evidence_path, expected_sources in specs:
        panel = json.loads(panel_path.read_text(encoding="utf-8"))
        records = list(panel.get("records") or [])
        if len(records) != expected_sources:
            raise ValueError(f"refusing {panel_name}: expected {expected_sources} exposed sources")
        evidence = _evidence_map(evidence_path)
        panel_keys = {(int(row["seed"]), seat) for row in records for seat in (0, 1)}
        if set(evidence) != panel_keys:
            raise ValueError(f"refusing {panel_name}: oracle evidence does not exactly cover panel")
        for source in records:
            for seat in (0, 1):
                key = (int(source["seed"]), seat)
                tasks.append({
                    "registry": str(args.registry.resolve()),
                    "panel_name": panel_name,
                    "candidate": candidate_id,
                    "source": dict(source),
                    "candidate_seat": seat,
                    "evidence": evidence[key],
                    "max_orders": int(args.max_orders),
                })
    if args.limit:
        tasks = tasks[: int(args.limit)]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    games = []
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = {pool.submit(_run_game, task): task for task in tasks}
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 8 == 0 or index == len(futures):
                print(f"[shadow-calibration] {index}/{len(futures)}", flush=True)
    games.sort(key=lambda row: (row["panel"], int(row["source"]["seed"]), int(row["candidate_seat"])))
    opportunities = [item for game in games for item in game.pop("opportunities")]
    opportunities.sort(
        key=lambda row: (row["panel"], int(row["source"]["seed"]), int(row["candidate_seat"]), int(row["step"]))
    )
    prefix = args.panel
    games_path = args.output_dir / f"{prefix}_games.jsonl"
    opportunities_path = args.output_dir / f"{prefix}_opportunities.jsonl"
    summary_path = args.output_dir / f"{prefix}_summary.json"
    games_sha = _write_jsonl(games_path, games)
    opportunities_sha = _write_jsonl(opportunities_path, opportunities)
    summary = _summarise(opportunities, games)
    summary["games_file"] = str(games_path.resolve())
    summary["games_sha256"] = games_sha
    summary["opportunities_file"] = str(opportunities_path.resolve())
    summary["opportunities_sha256"] = opportunities_sha
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "summary": str(summary_path.resolve()),
        "games": len(games),
        "opportunities": len(opportunities),
        "all_replays_match": summary["all_replays_match_existing_oracle"],
        "recommended_gate": summary["recommended_preregistered_gate"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
