"""Diagnostic only: attribute V120's state transforms over its selected route.

Set ``DIAG_CHAIN`` from 0 through 7.  This file deliberately imports V120 and
is therefore never a promotable candidate; it only identifies which causal
rules must be reimplemented in the independent Top20 HMoE.
"""

from __future__ import annotations

import copy
import importlib.util
import os
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[2] / "v120_hierarchical_top5_distillation/main.py"
SPEC = importlib.util.spec_from_file_location("v120_transform_diagnostic_source", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
ROUTE = MODULE._V120_DISTILLED_ROUTE


def agent(obs, configuration=None):
    del configuration
    step = int(obs.get("step", int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)) or 0)
    chain = max(0, min(7, int(os.environ.get("DIAG_CHAIN", "0"))))
    mask = {value.strip() for value in os.environ.get("DIAG_MASK", "").split(",") if value.strip()}
    enabled = lambda name, stage: name in mask if mask else chain >= stage
    MODULE._ACTIONS = ROUTE
    action = copy.deepcopy(ROUTE[min(step, len(ROUTE) - 1)])

    if enabled("weed", 1):
        action = MODULE._weed_repair_action(obs, action, step)
    if enabled("feed", 1):
        action = MODULE._v17_feed_guard(obs, action, step)
    if enabled("evac", 1):
        action = MODULE._v17_room_evac(obs, action, step)
    if enabled("repay", 2):
        action = MODULE._repay_shift(obs, action, step)
    if enabled("rank", 2):
        action = MODULE._rank_sell_slots(obs, action, None)
    if enabled("preempt", 2):
        action = MODULE._preempt_shift(obs, action, step)
    if enabled("front", 3):
        action = MODULE._v45_terminal_inventory_front_run(obs, action, step)
    if enabled("r5", 3):
        action = MODULE._v17_r5_counter(obs, action, step)
    if enabled("md", 3):
        action = MODULE._v17_md_counter(obs, action, step)
    if enabled("room", 3):
        action = MODULE._v17_room_guard(obs, action, step)
    if enabled("liquidate", 4):
        action = MODULE._terminal_liquidation(obs, action, step)
    if enabled("fulfill", 4):
        action = MODULE._fulfill_planned_sell_from_idle_carrier(obs, action)
    if enabled("rerank", 4):
        action = MODULE._rank_sell_slots(obs, action, None)
    if enabled("premium", 4):
        action = MODULE._bubble_premium_over_non_sells(action)
    if enabled("sellbubble", 4):
        action = MODULE._bubble_sells_over_fixed_spends(action, obs)
    if enabled("merge", 4):
        action = MODULE._merge_duplicate_sells(action)
    if enabled("prebuy", 5):
        action = MODULE._wheat_demand_prebuy(obs, action, step)
    if enabled("carrot", 5):
        action = MODULE._prune_carrot_seed_surplus(obs, action, step)
    if enabled("wheatprune", 5):
        action = MODULE._prune_terminal_wheat_seed(obs, action, step)
    action = MODULE._align_hands(action, obs)
    if enabled("v76", 6):
        action = MODULE._v76_adjacent_safe_buy_lead(obs, action)
    if enabled("v118", 7):
        action = MODULE._v118_reveal_liquidity(obs, action, step)
    return action


def model_status():
    return {
        "diagnostic_only": True,
        "imports_v120": True,
        "promotable": False,
        "chain": int(os.environ.get("DIAG_CHAIN", "0")),
    }
