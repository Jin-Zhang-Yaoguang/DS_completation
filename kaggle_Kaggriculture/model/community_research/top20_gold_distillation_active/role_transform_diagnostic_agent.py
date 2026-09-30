"""Diagnostic-only V120 transform overlay on the recovered role executor."""

from __future__ import annotations

import importlib.util
import copy
import os
from pathlib import Path


HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROLE = _load("role_transform_diagnostic_base", HERE / "role_option_agent.py")
V120 = _load("role_transform_diagnostic_v120", HERE.parents[1] / "v120_hierarchical_top5_distillation/main.py")
QUEUE = _load("role_transform_diagnostic_queue", HERE.parents[1] / "v14_first_principles_search/prototype_queue_solver.py")


def agent(obs, configuration=None):
    step = int(obs.get("step", int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)) or 0)
    action = ROLE.agent(obs, configuration)
    mask = {value.strip() for value in os.environ.get("ROLE_DIAG_MASK", "").split(",") if value.strip()}
    if "functioncore" in mask:
        names = {value.strip() for value in os.environ.get("ROLE_CORE_FUNCTIONS", "").split(",") if value.strip()}
        V120._ACTIONS = V120._V120_DISTILLED_ROUTE
        if "repay" in names: action = V120._repay_shift(obs, action, step)
        if "rank1" in names: action = V120._rank_sell_slots(obs, action, None)
        if "preempt" in names: action = V120._preempt_shift(obs, action, step)
        if "front" in names: action = V120._v45_terminal_inventory_front_run(obs, action, step)
        if "r5" in names: action = V120._v17_r5_counter(obs, action, step)
        if "md" in names: action = V120._v17_md_counter(obs, action, step)
        if "room" in names: action = V120._v17_room_guard(obs, action, step)
        if "liquidate" in names: action = V120._terminal_liquidation(obs, action, step)
        if "fulfill" in names: action = V120._fulfill_planned_sell_from_idle_carrier(obs, action)
        if "rank2" in names: action = V120._rank_sell_slots(obs, action, None)
        if "premium" in names: action = V120._bubble_premium_over_non_sells(action)
        if "sellbubble" in names: action = V120._bubble_sells_over_fixed_spends(action, obs)
        if "merge" in names: action = V120._merge_duplicate_sells(action)
        action = V120._align_hands(action, obs)
    if "partialcore" in mask:
        stages = set(os.environ.get("ROLE_CORE_STAGES", ""))
        V120._ACTIONS = V120._V120_DISTILLED_ROUTE
        if "1" in stages:
            action = V120._weed_repair_action(obs, action, step)
            action = V120._v17_feed_guard(obs, action, step)
            action = V120._v17_room_evac(obs, action, step)
        if "2" in stages:
            action = V120._repay_shift(obs, action, step)
            action = V120._rank_sell_slots(obs, action, None)
            action = V120._preempt_shift(obs, action, step)
        if "3" in stages:
            action = V120._v45_terminal_inventory_front_run(obs, action, step)
            action = V120._v17_r5_counter(obs, action, step)
            action = V120._v17_md_counter(obs, action, step)
            action = V120._v17_room_guard(obs, action, step)
        if "4" in stages:
            action = V120._terminal_liquidation(obs, action, step)
            action = V120._fulfill_planned_sell_from_idle_carrier(obs, action)
            action = V120._rank_sell_slots(obs, action, None)
            action = V120._bubble_premium_over_non_sells(action)
            action = V120._bubble_sells_over_fixed_spends(action, obs)
            action = V120._merge_duplicate_sells(action)
        if "5" in stages:
            action = V120._wheat_demand_prebuy(obs, action, step)
            action = V120._prune_carrot_seed_surplus(obs, action, step)
            action = V120._prune_terminal_wheat_seed(obs, action, step)
        action = V120._align_hands(action, obs)
    if "allcore" in mask:
        V120._ACTIONS = V120._V120_DISTILLED_ROUTE
        action = V120._weed_repair_action(obs, action, step)
        action = V120._v17_feed_guard(obs, action, step)
        action = V120._v17_room_evac(obs, action, step)
        action = V120._repay_shift(obs, action, step)
        action = V120._rank_sell_slots(obs, action, None)
        action = V120._preempt_shift(obs, action, step)
        action = V120._v45_terminal_inventory_front_run(obs, action, step)
        action = V120._v17_r5_counter(obs, action, step)
        action = V120._v17_md_counter(obs, action, step)
        action = V120._v17_room_guard(obs, action, step)
        action = V120._terminal_liquidation(obs, action, step)
        action = V120._fulfill_planned_sell_from_idle_carrier(obs, action)
        action = V120._rank_sell_slots(obs, action, None)
        action = V120._bubble_premium_over_non_sells(action)
        action = V120._bubble_sells_over_fixed_spends(action, obs)
        action = V120._merge_duplicate_sells(action)
        action = V120._wheat_demand_prebuy(obs, action, step)
        action = V120._prune_carrot_seed_surplus(obs, action, step)
        action = V120._prune_terminal_wheat_seed(obs, action, step)
        action = V120._align_hands(action, obs)
    if "rank" in mask:
        action = V120._rank_sell_slots(obs, action, None)
    if "preempt" in mask:
        V120._ACTIONS = V120._V120_DISTILLED_ROUTE
        action = V120._repay_shift(obs, action, step)
        action = V120._preempt_shift(obs, action, step)
    if "premium" in mask:
        action = V120._bubble_premium_over_non_sells(action)
    if "sellbubble" in mask:
        action = V120._bubble_sells_over_fixed_spends(action, obs)
    if "merge" in mask:
        action = V120._merge_duplicate_sells(action)
    if "v76" in mask:
        action = V120._v76_adjacent_safe_buy_lead(obs, action)
    if "bestresponse" in mask:
        opponent_obs = copy.deepcopy(obs)
        opponent_obs["player"] = 1 - int(obs.get("player", 0) or 0)
        opponent_obs["private"] = copy.deepcopy(obs.get("private") or {})
        action, _, _ = QUEUE._best_sell_permutation(obs, action, action, opponent_obs)
    return action


def model_status():
    return {"diagnostic_only": True, "imports_v120": True, "promotable": False}
