"""Self-contained Kaggriculture serving entrypoint for the frozen r002 incumbent.

This file intentionally makes no policy change.  It runs the V10 learned
full-expert router and then applies the exact V11 ``topday_animal_throttle``
residual: on days 10, 17 and 24, existing EGG/MILK/WOOL sell quantities are
multiplied by 0.5 using Python's ``round`` semantics.  Farmer, hand, route,
purchase and non-animal market decisions remain owned by the frozen parent.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from typing import Any, Mapping


if "__file__" in globals():
    # Normal module import (local tooling and source/factory validation).
    HERE = Path(globals()["__file__"]).resolve().parent
else:
    # Kaggle's get_last_callable executes raw main.py with ``env = {}`` and
    # appends the archive extraction directory to sys.path for that exec.
    HERE = Path(sys.path[-1]).resolve()
MODEL_ROOT = HERE.parent
SOURCE_REGISTRY = (
    MODEL_ROOT
    / "v11_iterative_league"
    / "runs"
    / "round_002"
    / "strategy"
    / "registry_next.json"
)

MODEL_ID = "v12_incumbent_r002"
SOURCE_MODEL_ID = "r002_learned_router_topday_animal_throttle"
ROUTER_PARENT_ID = "learned_router"
SOURCE_SERVING_SHA256 = "38afb12bd5fbc987adf752acb437abe9330bd385233c22782b35353f77be2d74"
ROUTER_PARENT_SERVING_SHA256 = "9813b175856c8e702613bb27b4e0a4b95403cae65093615d9611f12cdb184ed6"
TOP_DAYS = frozenset({10, 17, 24})
ANIMAL_PRODUCTS = frozenset({"EGG", "MILK", "WOOL"})
SELL_FRACTION = 0.5


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _step(obs: Any) -> int:
    return int(_get(obs, "step", 0) or 0)


def _canonical_action(
    action: Mapping[str, Any] | None,
) -> dict[str, list[Any]]:
    """Exact copy of V11 mutation_catalog.canonical_action."""

    source = copy.deepcopy(dict(action or {}))
    return {
        "farmer": list(source.get("farmer") or ["PASS"]),
        "hands": [
            list(item or ["PASS"]) for item in (source.get("hands") or [])
        ],
        "market": [list(item) for item in (source.get("market") or [])],
    }


def _topday_animal_throttle(
    action: Mapping[str, Any], obs: Any
) -> dict[str, list[Any]]:
    """Exact r002 residual, kept local so the archive has no V11 dependency."""

    result = _canonical_action(action)
    day = int(_get(obs, "day", _step(obs) // 24) or 0)
    if day not in TOP_DAYS:
        return result
    filtered: list[list[Any]] = []
    for order in result["market"]:
        if (
            len(order) >= 3
            and str(order[0]) == "SELL"
            and str(order[1]) in ANIMAL_PRODUCTS
        ):
            order[2] = int(round(int(order[2] or 0) * SELL_FRACTION))
            if int(order[2]) <= 0:
                continue
        filtered.append(order)
    result["market"] = filtered[:10]
    return result


def _load_router_from_bundle() -> Any:
    runtime = HERE / "runtime"
    policy_path = runtime / "policy.json"
    if not policy_path.is_file():
        return None
    sys.path.insert(0, str(runtime))
    try:
        import fast_router  # type: ignore

        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        return fast_router.create_agent(
            policy["router_spec"],
            policy["expert_specs"],
            str(runtime),
        )
    finally:
        sys.path.pop(0)


def _load_router_from_repository() -> Any:
    from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
        create_agent as create_registered_agent,
        load_registry,
    )

    return create_registered_agent(load_registry(SOURCE_REGISTRY), ROUTER_PARENT_ID)


def _load_router() -> Any:
    bundled = _load_router_from_bundle()
    return bundled if bundled is not None else _load_router_from_repository()


def _diagnostics(agent: Any) -> dict[str, Any]:
    method = getattr(agent, "diagnostics", None)
    return dict(method()) if callable(method) else {}


class IncumbentAgent:
    """Episode-local materialization of the exact r002 serving path."""

    def __init__(self) -> None:
        self.parent = _load_router()
        self.calls = 0
        self.changed_actions = 0
        self.last_step = -1

    def __call__(
        self, obs: Any, configuration: Any = None
    ) -> dict[str, list[Any]]:
        self.last_step = _step(obs)
        before = self.parent(obs, configuration)
        after = _topday_animal_throttle(before, obs)
        self.calls += 1
        if json.dumps(before, sort_keys=True, separators=(",", ":")) != json.dumps(
            after, sort_keys=True, separators=(",", ":")
        ):
            self.changed_actions += 1
        return after

    def diagnostics(self) -> dict[str, Any]:
        return {
            "kind": "v12_requalified_v11_incumbent",
            "model_id": MODEL_ID,
            "source_model_id": SOURCE_MODEL_ID,
            "source_serving_sha256": SOURCE_SERVING_SHA256,
            "router_parent_id": ROUTER_PARENT_ID,
            "router_parent_serving_sha256": ROUTER_PARENT_SERVING_SHA256,
            "calls": self.calls,
            "changed_actions": self.changed_actions,
            "last_step": self.last_step,
            "policy_changed": False,
            "parent_diagnostics": _diagnostics(self.parent),
        }


def make_agent() -> IncumbentAgent:
    return IncumbentAgent()


_AGENT: IncumbentAgent | None = None


def model_status() -> dict[str, Any]:
    if _AGENT is None:
        return {
            "kind": "v12_requalified_v11_incumbent",
            "model_id": MODEL_ID,
            "source_model_id": SOURCE_MODEL_ID,
            "policy_changed": False,
            "status": "not_started",
        }
    return _AGENT.diagnostics()


def agent(obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
    """Kaggle entrypoint and intentionally the file's last callable."""

    global _AGENT
    step = _step(obs)
    if _AGENT is None or step == 0 or step < _AGENT.last_step:
        _AGENT = make_agent()
    return _AGENT(obs, configuration)
