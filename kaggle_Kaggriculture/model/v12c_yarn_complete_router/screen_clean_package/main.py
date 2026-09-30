"""Kaggriculture V12C: observable YARN complete-expert router.

This policy keeps the shared 72-step opening of the frozen V5 and V8 complete
experts.  At step 72 it makes one public, auditable choice for the rest of the
season:

* if YARN_STORE is already unlocked, run the complete V5 expert;
* otherwise run the complete V8 expert.

The rule is intentionally one-shot.  It does not splice worker plans, tune a
price threshold, or add any market-order residual.  Both experts are advanced
on the actually reached observations through the decision boundary, and only
the selected expert is advanced afterwards.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
V10 = MODEL_ROOT / "v10_replay_lolo_router"
SOURCE_REGISTRY = V10 / "final_registry.json"

MODEL_ID = "v12c_yarn_complete_router"
ANCHOR_ID = "baseline_v8"
YARN_ID = "baseline_v5"
SWITCH_STEP = 72


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _step(obs: Any) -> int:
    return int(_get(obs, "step", 0) or 0)


def _canonical_action(action: Mapping[str, Any] | None) -> dict[str, list[Any]]:
    raw = copy.deepcopy(dict(action or {}))
    return {
        "farmer": list(raw.get("farmer") or ["PASS"]),
        "hands": [list(item or ["PASS"]) for item in (raw.get("hands") or [])],
        "market": [list(item or []) for item in (raw.get("market") or [])],
    }


def _action_bytes(action: Mapping[str, Any]) -> bytes:
    return json.dumps(
        _canonical_action(action),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _unlocked_shops(obs: Any) -> tuple[str, ...]:
    town = _get(obs, "town", {}) or {}
    return tuple(str(item) for item in (_get(town, "unlocked_shops", []) or []))


def _load_experts_from_bundle() -> dict[str, Any] | None:
    runtime = HERE / "runtime"
    policy_path = runtime / "policy.json"
    if not policy_path.is_file():
        return None
    sys.path.insert(0, str(runtime))
    try:
        import agent_factory  # type: ignore

        payload = json.loads(policy_path.read_text(encoding="utf-8"))
        models = {
            str(key): dict(value)
            for key, value in dict(payload["expert_specs"]).items()
        }
        registry = agent_factory.Registry(
            path=runtime / "_embedded_registry.json",
            models=models,
            raw={"models": list(models.values())},
        )
        return {
            model_id: agent_factory.create_agent(registry, model_id)
            for model_id in (ANCHOR_ID, YARN_ID)
        }
    finally:
        sys.path.pop(0)


def _load_experts_from_repository() -> dict[str, Any]:
    from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
        create_agent,
        load_registry,
    )

    registry = load_registry(SOURCE_REGISTRY)
    return {
        model_id: create_agent(registry, model_id)
        for model_id in (ANCHOR_ID, YARN_ID)
    }


def _load_experts() -> dict[str, Any]:
    bundled = _load_experts_from_bundle()
    return bundled if bundled is not None else _load_experts_from_repository()


class YarnCompleteRouterAgent:
    """One-shot public-shop router over two complete, state-isolated experts."""

    def __init__(self, *, switch_step: int = SWITCH_STEP) -> None:
        if int(switch_step) < 1:
            raise ValueError("switch_step must be positive")
        self.switch_step = int(switch_step)
        self.experts = _load_experts()
        self._reset()

    def _reset(self) -> None:
        self.last_step = -1
        self.calls = 0
        self.selected: str | None = None
        self.selection_reason = "not_reached"
        self.selection_shops: tuple[str, ...] = ()
        self.prefix_steps: set[int] = set()
        self.prefix_match = True
        self.prefix_first_mismatch: int | None = None
        self.runtime_errors: list[str] = []
        self.selected_fallbacks = 0

    def __call__(self, obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
        step = _step(obs)
        if step == 0 or step < self.last_step:
            self._reset()
        self.last_step = step
        self.calls += 1

        if self.selected is not None and step > self.switch_step:
            try:
                return _canonical_action(
                    self.experts[self.selected](obs, configuration)
                )
            except Exception as exc:
                self.runtime_errors.append(
                    f"step={step}:{type(exc).__name__}:{exc}"
                )
                self.selected_fallbacks += 1
                return {"farmer": ["PASS"], "hands": [], "market": []}

        actions: dict[str, dict[str, list[Any]]] = {}
        for model_id, expert in self.experts.items():
            try:
                actions[model_id] = _canonical_action(expert(obs, configuration))
            except Exception as exc:
                self.runtime_errors.append(
                    f"{model_id}:step={step}:{type(exc).__name__}:{exc}"
                )

        anchor = actions.get(ANCHOR_ID)
        if anchor is None:
            self.selected_fallbacks += 1
            return {"farmer": ["PASS"], "hands": [], "market": []}

        if step < self.switch_step:
            self.prefix_steps.add(step)
            yarn_action = actions.get(YARN_ID)
            if yarn_action is None or _action_bytes(yarn_action) != _action_bytes(anchor):
                self.prefix_match = False
                if self.prefix_first_mismatch is None:
                    self.prefix_first_mismatch = step
            return anchor

        if self.selected is None:
            self.selection_shops = _unlocked_shops(obs)
            prefix_complete = self.prefix_steps == set(range(self.switch_step))
            yarn_eligible = (
                prefix_complete
                and self.prefix_match
                and YARN_ID in actions
                and not any(item.startswith(f"{YARN_ID}:") for item in self.runtime_errors)
            )
            if "YARN_STORE" in self.selection_shops and yarn_eligible:
                self.selected = YARN_ID
                self.selection_reason = "observed_yarn_store"
            else:
                self.selected = ANCHOR_ID
                self.selection_reason = (
                    "no_yarn_store"
                    if "YARN_STORE" not in self.selection_shops
                    else "prefix_or_yarn_expert_fallback"
                )

        chosen = actions.get(self.selected)
        if chosen is None:
            self.selected_fallbacks += 1
            return {"farmer": ["PASS"], "hands": [], "market": []}
        return chosen

    def diagnostics(self) -> dict[str, Any]:
        return {
            "kind": "observable_complete_expert_router",
            "model_id": MODEL_ID,
            "switch_step": self.switch_step,
            "anchor": ANCHOR_ID,
            "yarn_expert": YARN_ID,
            "selected": self.selected,
            "selection_reason": self.selection_reason,
            "selection_shops": list(self.selection_shops),
            "prefix_complete": self.prefix_steps == set(range(self.switch_step)),
            "prefix_match": self.prefix_match,
            "prefix_first_mismatch": self.prefix_first_mismatch,
            "calls": self.calls,
            "runtime_errors": list(self.runtime_errors),
            "selected_fallbacks": self.selected_fallbacks,
            "post_switch_policy": "selected_complete_expert_only",
        }


def make_agent() -> YarnCompleteRouterAgent:
    return YarnCompleteRouterAgent()


_AGENT = make_agent()


def agent(obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
    return _AGENT(obs, configuration)

