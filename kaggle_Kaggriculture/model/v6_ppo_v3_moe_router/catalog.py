"""Runnable, flat expert catalog for local PPO v3 data collection and serving.

Each production expert owns an isolated copy of the V1 module.  This prevents
the baseline action used by the compiler from mutating the state of a selected
route expert, and makes forked simulations snapshot-able.
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any, Mapping

from experts import (
    CallableMarketExpert,
    RouteTemplateProductionExpert,
    V1ProductionExpert,
    register_market_expert,
    register_production_expert,
)


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
# A clean Kaggle archive supplies a copied `v1_agent.py`; source development
# falls back to the canonical V1 directory without coupling the archive to it.
V1_SOURCE = HERE / "v1_agent.py"
if not V1_SOURCE.exists():
    V1_SOURCE = MODEL_ROOT / "v1_adaptive_market" / "main.py"
_STATE_NAMES = (
    "_WEED_STATE", "_SHIFT_STATE", "_V17_R5_STATE", "_V17_MD_STATE",
    "_V17_FEED_RESCUE_STATE", "_V17_ROOM_EVAC_STATE", "_WHEAT_PREBUY_STATE", "_ROUTE_STATE",
)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load expert source: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IsolatedRouteAgent:
    """A cloneable module-backed V1/LOW/HIGH complete-plan expert."""

    def __init__(self, route: str, module_name: str) -> None:
        if route not in {"adaptive", "low", "high"}:
            raise ValueError(route)
        self.route = route
        self.module = _load_module(V1_SOURCE, module_name)

    def __call__(self, obs: Mapping[str, Any]):
        if self.route == "adaptive":
            return self.module.agent(obs)
        self.module._ACTIONS = self.module._LOW_ROUTE_ACTIONS if self.route == "low" else self.module._HIGH_ROUTE_ACTIONS
        return self.module._CORE_AGENT(obs)

    def snapshot(self):
        values = {name: copy.deepcopy(getattr(self.module, name)) for name in _STATE_NAMES if hasattr(self.module, name)}
        values["_ACTIONS_ROUTE"] = self.route
        return values

    def restore(self, state):
        for name, value in dict(state or {}).items():
            if name in _STATE_NAMES:
                setattr(self.module, name, copy.deepcopy(value))
        if self.route == "low":
            self.module._ACTIONS = self.module._LOW_ROUTE_ACTIONS
        elif self.route == "high":
            self.module._ACTIONS = self.module._HIGH_ROUTE_ACTIONS


def _day(obs) -> int:
    return int((obs or {}).get("day", int((obs or {}).get("step", 0) or 0) // 24) or 0)


def _has_sell(action, items=None):
    allowed = set(items or ())
    return any(
        len(order) >= 3 and order[0] == "SELL" and (not allowed or str(order[1]) in allowed) and int(order[2] or 0) > 0
        for order in list((action or {}).get("market", []) or [])
    )


def _animal_half(action, obs):
    result = copy.deepcopy(action)
    for order in result.get("market", []):
        if len(order) >= 3 and order[0] == "SELL" and str(order[1]) in {"EGG", "MILK", "WOOL"}:
            order[2] = max(0, int(round(int(order[2] or 0) * 0.5)))
    return result


# This schedule is deliberately part of the expert definition, rather than a
# hidden serving-side override.  A prior independent, same-state audit found
# a positive intervention effect only at these three mid-season decision
# points.  Applying the same half-sale residual on *every* selling day was
# materially harmful in D1, so that broad policy is not routable.
ANIMAL_HALF_TOPDAYS = (10, 17, 24)


def _animal_half_topdays(action, obs):
    """Apply the audited animal-sale residual only on its registered days."""
    return _animal_half(action, obs)


def _premium_first(action, obs):
    result = copy.deepcopy(action)
    prices = dict(((obs or {}).get("market", {}) or {}).get("prices", {}) or {})
    sell_at = [i for i, order in enumerate(result.get("market", [])) if len(order) >= 3 and order[0] == "SELL"]
    sells = [result["market"][i] for i in sell_at]
    sells.sort(key=lambda order: float(prices.get(str(order[1]), 0) or 0), reverse=True)
    for index, order in zip(sell_at, sells):
        result["market"][index] = order
    return result


def _wheat_reserve(action, obs):
    result = copy.deepcopy(action)
    for order in result.get("market", []):
        if len(order) >= 3 and order[0] == "SELL" and str(order[1]) == "WHEAT":
            order[2] = max(0, int(order[2] or 0) - 4)
    return result


class Catalog:
    """Per-episode catalog with isolated full-plan production experts."""

    # ``_LOW_ROUTE_ACTIONS`` is the exact V1 action trace, so exposing it as
    # a routable expert would create a duplicate action with a different ID.
    # It remains available as a deterministic opponent family, but is not a
    # learnable production choice.
    # E_HIGH failed the formal D1 gate and is retained only as an opponent
    # implementation.  Do not leave it in this serving contract: otherwise
    # a D2-trained one-column production head correctly fails closed on a
    # positional schema mismatch.
    production_names = ("E_V1",)
    # D1 rejected the three broad, always-on residuals.  Keep only the
    # pre-registered, time-bounded intervention in the trainable catalog.
    # Rejected variants remain in the D1 JSON as negative evidence rather
    # than being silently reintroduced through a positional action column.
    market_names = ("M_NONE", "M_ANIMAL_HALF_TOPDAYS")

    def __init__(self, namespace: str = "ppo_v3") -> None:
        self.v1 = IsolatedRouteAgent("adaptive", namespace + "_v1")
        self.low = IsolatedRouteAgent("low", namespace + "_low")
        self.high = IsolatedRouteAgent("high", namespace + "_high")
        self.production = {
            "E_V1": V1ProductionExpert(self.v1, "E_V1"),
        }
        self.market = {
            "M_ANIMAL_HALF_TOPDAYS": CallableMarketExpert(
                "M_ANIMAL_HALF_TOPDAYS", _animal_half_topdays,
                predicate=lambda obs: _day(obs) in ANIMAL_HALF_TOPDAYS,
                description="halve animal-product sells only on audited days 10/17/24",
            ),
        }

    def register_global(self) -> None:
        """Optional adapter for utilities that use the module-level registry."""
        for expert in self.production.values():
            register_production_expert(expert, replace=True)
        for expert in self.market.values():
            register_market_expert(expert, replace=True)

    def snapshot(self):
        return {"v1": self.v1.snapshot(), "low": self.low.snapshot(), "high": self.high.snapshot()}

    def restore(self, state) -> None:
        self.v1.restore(dict(state or {}).get("v1", {}))
        self.low.restore(dict(state or {}).get("low", {}))
        self.high.restore(dict(state or {}).get("high", {}))

    def baseline(self, obs):
        return self.production["E_V1"].propose(obs)

    def production_proposal(self, expert_id: str, obs):
        return self.production[str(expert_id)].propose(obs)

    def market_proposal(self, expert_id: str | None, obs, production):
        if expert_id in (None, "", "M_NONE"):
            return None, None
        expert = self.market[str(expert_id)]
        return expert, expert.propose(obs, production)
