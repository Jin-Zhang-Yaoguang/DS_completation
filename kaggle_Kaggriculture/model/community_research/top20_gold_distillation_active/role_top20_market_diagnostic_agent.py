"""Research composition: role-option units plus the all-Top20 market HMoE."""

from __future__ import annotations

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROLE = _load("role_top20_market_units", HERE / "role_option_agent.py")
HMOE = _load("role_top20_market_hmoe", HERE / "main.py")


def agent(obs, configuration=None):
    action = ROLE.agent(obs, configuration)
    seat = ROLE._seat(obs)
    day, hour = ROLE._int(obs.get("day")), ROLE._int(obs.get("hour"))
    step = day * 24 + hour
    hstate = HMOE._reset(dict(obs), step)
    HMOE._select_contracts(dict(obs), hstate, day, hour)
    positions = HMOE._positions(HMOE._farm(obs))
    inventories = HMOE._inventories(obs, len(positions))
    action["market"] = HMOE._market(dict(obs), hstate, day, hour, inventories)
    rstate = ROLE._STATE[seat]
    action = ROLE._causal_market_compiler(obs, action, step, rstate)
    rstate["last_step"] = step
    return action


def model_status():
    return {
        "research_only": True,
        "unit_source": "daily_role_option_state_recovery",
        "market_source": "all_top20_global_daily_rule_tree",
        "tape": False,
        "promotable": False,
    }
