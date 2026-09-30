"""Frozen-release candidate: Top20-selected Whyme role/phase HMoE."""
from __future__ import annotations

import whyme_phase_core as CORE


STATE = {0: {}, 1: {}}


def agent(obs, configuration=None):
    action = CORE.agent(obs, configuration)
    seat = 1 if int(obs.get("player", 0) or 0) == 1 else 0
    step = int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)
    state = STATE[seat]
    if step == 0 or step <= int(state.get("last", -1)):
        state.clear()
    state["last"] = step
    action = CORE._room_guard(obs, action, step)
    action = CORE._terminal_liquidate(obs, action, step)
    action = CORE._rank_sales(obs, action)
    return CORE._sell_bubble(action)


def model_status():
    return {
        "kind": "top20_whyme_six_hour_role_phase_hmoe",
        "strategy_parent": None,
        "teacher_panel_size": 20,
        "selected_teacher": "Whyme Labs",
        "unit_tape": False,
        "market_tape": False,
        "step_lookup": False,
        "future_features": False,
        "router": "daily_role_queue_plus_six_hour_market_phase",
        "experts": [
            "role_path",
            "resource_budget",
            "market_queue",
            "room_guard",
            "terminal_liquidation",
        ],
        "promotable": True,
    }
