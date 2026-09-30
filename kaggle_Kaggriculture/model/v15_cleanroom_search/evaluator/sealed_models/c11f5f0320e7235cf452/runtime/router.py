"""One-shot full-expert routers for Kaggriculture V10.

The router does not splice worker orders or blend plans.  It shadows every
complete expert from step 0, verifies that their first ``switch_step`` actions
are identical on the actually reached states, then selects exactly one expert
at the boundary.  The selected expert owns the remainder of the season.

Both selectors consume only fields visible in the submitted observation.
Notably, the learned selector never reads ``obs.private``.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

try:
    from .agent_factory import Registry, create_agent, resolve_path
except ImportError:  # direct-script compatibility
    from agent_factory import Registry, create_agent, resolve_path


FEATURE_SCHEMA = "kaggriculture-v10-public-step72-1"
ROUTER_WEIGHT_SCHEMA = "kaggriculture-v10-linear-router-1"
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("COW", "SHEEP", "GOOSE")
STRUCTURES = ("PASTURE", "COOP")
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
SHOPS = ("BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE", "ICE_CREAM_SHOP", "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET")
BASE_PRICES = {
    "WHEAT": 25.0, "CARROT": 35.0, "TOMATO": 60.0, "STRAWBERRY": 120.0,
    "MELON": 250.0, "EGG": 50.0, "MILK": 160.0, "WOOL": 200.0,
    "FERTILIZER": 100.0,
}

FEATURE_NAMES: list[str] = ["day", "hour", "seat"]
for prefix in ("self", "opponent"):
    FEATURE_NAMES += [f"{prefix}.money", f"{prefix}.hands", f"{prefix}.hires_today", f"{prefix}.unlocked"]
    FEATURE_NAMES += [f"{prefix}.crop.{item}" for item in CROPS]
    FEATURE_NAMES += [f"{prefix}.animal.{item}" for item in ANIMALS]
    FEATURE_NAMES += [f"{prefix}.structure.{item}" for item in STRUCTURES]
    FEATURE_NAMES += [f"{prefix}.weed", f"{prefix}.at_risk"]
for item in PRODUCTS:
    FEATURE_NAMES += [f"market.{item}.price_ratio", f"market.{item}.inventory_delta"]
FEATURE_NAMES += [f"shop.{item}" for item in SHOPS]
FEATURE_DIM = len(FEATURE_NAMES)


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _seat(obs: Any) -> int:
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _tile_counts(farm: Any) -> dict[str, float]:
    values = {f"crop.{item}": 0.0 for item in CROPS}
    values.update({f"animal.{item}": 0.0 for item in ANIMALS})
    values.update({f"structure.{item}": 0.0 for item in STRUCTURES})
    values.update({"weed": 0.0, "at_risk": 0.0})
    for row in list(_get(farm, "tiles", []) or []):
        for tile in list(row or []):
            if not isinstance(tile, Mapping):
                continue
            crop = str(tile.get("crop") or "")
            animal = str(tile.get("animal") or "")
            kind = str(tile.get("kind") or "")
            if crop in CROPS:
                values[f"crop.{crop}"] += 1.0
                if int(tile.get("consecutive_unwatered", 0) or 0) >= 1 and not bool(tile.get("watered_today", False)):
                    values["at_risk"] += 1.0
            if animal in ANIMALS:
                values[f"animal.{animal}"] += 1.0
                if int(tile.get("consecutive_unfed", 0) or 0) >= 1 and not bool(tile.get("fed_today", False)):
                    values["at_risk"] += 1.0
            if kind in STRUCTURES:
                values[f"structure.{kind}"] += 1.0
            if kind == "WEED":
                values["weed"] += 1.0
    return values


def public_features(obs: Any) -> np.ndarray:
    """Encode public/current observation fields only; ``private`` is ignored."""
    values = {name: 0.0 for name in FEATURE_NAMES}
    player = _seat(obs)
    step = int(_get(obs, "step", 0) or 0)
    values["day"] = min(29, max(0, int(_get(obs, "day", step // 24) or 0))) / 29.0
    values["hour"] = min(23, max(0, int(_get(obs, "hour", step % 24) or 0))) / 23.0
    values["seat"] = float(player)
    farms = list(_get(obs, "farms", []) or [])
    if len(farms) != 2:
        raise ValueError("router expects two public farms")
    for prefix, index in (("self", player), ("opponent", 1 - player)):
        farm = farms[index]
        values[f"{prefix}.money"] = float(_get(farm, "money", 0.0) or 0.0) / 200000.0
        values[f"{prefix}.hands"] = len(_get(farm, "hands", []) or []) / 16.0
        values[f"{prefix}.hires_today"] = float(_get(farm, "hires_today", 0) or 0) / 16.0
        values[f"{prefix}.unlocked"] = len(_get(farm, "unlocked_quadrants", []) or []) / 4.0
        counts = _tile_counts(farm)
        for key, count in counts.items():
            values[f"{prefix}.{key}"] = count / 25.0
    market = _get(obs, "market", {}) or {}
    prices = _get(market, "prices", {}) or {}
    inventory = _get(market, "inventory", {}) or {}
    for item in PRODUCTS:
        values[f"market.{item}.price_ratio"] = float(_get(prices, item, BASE_PRICES[item]) or BASE_PRICES[item]) / BASE_PRICES[item]
        values[f"market.{item}.inventory_delta"] = (float(_get(inventory, item, 10000) or 10000) - 10000.0) / 10000.0
    town = _get(obs, "town", {}) or {}
    shops = [str(item) for item in (_get(town, "unlocked_shops", []) or [])]
    for item in SHOPS:
        values[f"shop.{item}"] = min(8, shops.count(item)) / 8.0
    vector = np.asarray([values[name] for name in FEATURE_NAMES], dtype=np.float32)
    if vector.shape != (FEATURE_DIM,) or not np.all(np.isfinite(vector)):
        raise ValueError("invalid public router feature vector")
    return np.clip(vector, -5.0, 5.0)


def feature_mapping(vector: Sequence[float]) -> dict[str, float]:
    array = np.asarray(vector, dtype=np.float64)
    if array.shape != (FEATURE_DIM,):
        raise ValueError("invalid feature shape")
    return dict(zip(FEATURE_NAMES, array.tolist()))


def _copy_action(action: Any) -> dict[str, Any]:
    raw = copy.deepcopy(action or {})
    if not isinstance(raw, Mapping):
        raise TypeError("agent action is not a mapping")
    return {
        "farmer": list(_get(raw, "farmer", []) or ["PASS"]),
        "hands": [list(item or ["PASS"]) for item in (_get(raw, "hands", []) or [])],
        "market": [list(item or []) for item in (_get(raw, "market", []) or [])],
    }


def _action_bytes(action: Any) -> bytes:
    return json.dumps(_copy_action(action), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _priority_from_spec(spec: Mapping[str, Any], key: str, fallback: Sequence[str]) -> list[str]:
    rule = spec.get("rule") or {}
    values = rule.get(key) if isinstance(rule, Mapping) else None
    return [str(item) for item in (values or fallback)]


class RuleSelector:
    """Pre-registered, deterministic public-state routing rules."""

    def __init__(self, router_spec: Mapping[str, Any], expert_specs: Mapping[str, Mapping[str, Any]], anchor: str):
        self.spec = dict(router_spec)
        self.expert_specs = {str(k): dict(v) for k, v in expert_specs.items()}
        self.anchor = str(anchor)
        self.last_reason = "not_selected"

    def _tagged(self, tag: str, eligible: Sequence[str]) -> list[str]:
        return [item for item in eligible if tag in {str(x) for x in (self.expert_specs[item].get("tags") or [])}]

    def choose_vector(self, vector: Sequence[float], eligible: Sequence[str]) -> str:
        eligible = [str(item) for item in eligible]
        if not eligible:
            return self.anchor
        values = feature_mapping(vector)
        yarn = values.get("shop.YARN_STORE", 0.0) > 0.0
        # A near-zero bank balance is normal at step 72 for the shared opening;
        # it is not by itself a survival alarm.  A non-zero threshold must be
        # explicitly pre-registered by the rule spec.
        low_cash_threshold = float((self.spec.get("rule") or {}).get("low_cash", 0.0))
        low_cash = low_cash_threshold > 0.0 and values.get("self.money", 0.0) * 200000.0 < low_cash_threshold
        at_risk = values.get("self.at_risk", 0.0) > 0.0
        structure_distance = 0.0
        for suffix in [*(f"crop.{x}" for x in CROPS), *(f"animal.{x}" for x in ANIMALS), *(f"structure.{x}" for x in STRUCTURES)]:
            structure_distance += abs(values.get(f"self.{suffix}", 0.0) - values.get(f"opponent.{suffix}", 0.0)) * 25.0
        novelty_threshold = float((self.spec.get("rule") or {}).get("novelty_distance", 4.0))

        default = _priority_from_spec(self.spec, "default_priority", eligible)
        if low_cash or at_risk:
            priority = _priority_from_spec(self.spec, "survival_priority", self._tagged("survival", eligible) + default)
            reason = "public_survival_risk"
        elif yarn:
            priority = _priority_from_spec(self.spec, "yarn_priority", self._tagged("kawa", eligible) + default)
            reason = "public_yarn_signal"
        elif structure_distance > novelty_threshold:
            priority = _priority_from_spec(self.spec, "novel_priority", self._tagged("adaptive", eligible) + default)
            reason = "public_structure_novelty"
        else:
            priority, reason = default, "default_priority"
        for item in [*priority, *eligible]:
            if item in eligible:
                self.last_reason = reason
                return item
        self.last_reason = "anchor_fallback"
        return self.anchor if self.anchor in eligible else eligible[0]

    def choose(self, obs: Any, eligible: Sequence[str]) -> str:
        return self.choose_vector(public_features(obs), eligible)


class LearnedSelector:
    """Lightweight NumPy linear value model, one score per complete expert."""

    def __init__(self, weights: str | Path, anchor: str):
        data = np.load(Path(weights), allow_pickle=False)
        if str(data["schema"].item()) != ROUTER_WEIGHT_SCHEMA:
            raise ValueError("incompatible learned-router schema")
        if str(data["feature_schema"].item()) != FEATURE_SCHEMA:
            raise ValueError("incompatible learned-router feature schema")
        names = tuple(str(item) for item in data["feature_names"].tolist())
        if names != tuple(FEATURE_NAMES):
            raise ValueError("learned-router feature names do not match serving")
        self.classes = tuple(str(item) for item in data["classes"].tolist())
        self.mean = np.asarray(data["mean"], dtype=np.float32)
        self.scale = np.asarray(data["scale"], dtype=np.float32)
        self.coef = np.asarray(data["coef"], dtype=np.float32)
        self.intercept = np.asarray(data["intercept"], dtype=np.float32)
        if self.mean.shape != (FEATURE_DIM,) or self.scale.shape != (FEATURE_DIM,):
            raise ValueError("invalid learned-router normalisation")
        if self.coef.shape != (FEATURE_DIM, len(self.classes)) or self.intercept.shape != (len(self.classes),):
            raise ValueError("invalid learned-router coefficients")
        arrays = (self.mean, self.scale, self.coef, self.intercept)
        if not all(np.all(np.isfinite(item)) for item in arrays) or np.any(self.scale <= 0):
            raise ValueError("non-finite learned-router weights")
        self.anchor = str(anchor)
        self.last_scores: dict[str, float] = {}
        self.last_reason = "not_selected"

    def scores(self, vector: Sequence[float]) -> dict[str, float]:
        x = np.asarray(vector, dtype=np.float32)
        if x.shape != (FEATURE_DIM,) or not np.all(np.isfinite(x)):
            raise ValueError("invalid learned-router input")
        x = np.clip((x - self.mean) / self.scale, -8.0, 8.0)
        prediction = x @ self.coef + self.intercept
        self.last_scores = {name: float(prediction[index]) for index, name in enumerate(self.classes)}
        return dict(self.last_scores)

    def choose_vector(self, vector: Sequence[float], eligible: Sequence[str]) -> str:
        scores = self.scores(vector)
        valid = [(scores[item], -index, item) for index, item in enumerate(eligible) if item in scores and np.isfinite(scores[item])]
        if not valid:
            self.last_reason = "no_eligible_trained_class"
            return self.anchor if self.anchor in eligible else str(eligible[0])
        self.last_reason = "maximum_predicted_win_score"
        return max(valid)[2]

    def choose(self, obs: Any, eligible: Sequence[str]) -> str:
        return self.choose_vector(public_features(obs), eligible)


class ShadowRouter:
    """Shadow full experts, validate their prefix, then switch once."""

    def __init__(
        self,
        model_id: str,
        experts: Mapping[str, Any],
        expert_specs: Mapping[str, Mapping[str, Any]],
        anchor: str,
        selector: RuleSelector | LearnedSelector,
        switch_step: int = 72,
    ) -> None:
        if anchor not in experts:
            raise ValueError("router anchor is not an expert")
        if switch_step < 1:
            raise ValueError("switch_step must be positive")
        self.model_id = str(model_id)
        self.experts = dict(experts)
        self.expert_specs = {key: dict(value) for key, value in expert_specs.items()}
        self.anchor = str(anchor)
        self.selector = selector
        self.switch_step = int(switch_step)
        self._reset()

    def _reset(self) -> None:
        self.last_step = -1
        self.seen_prefix_steps: set[int] = set()
        self.prefix_match = {key: True for key in self.experts}
        self.prefix_first_mismatch: dict[str, int | None] = {key: None for key in self.experts}
        self.prefix_errors: dict[str, list[str]] = {key: [] for key in self.experts}
        self.prefix_hashes = {key: hashlib.sha256() for key in self.experts}
        self.selected: str | None = None
        self.selection_reason = "not_reached"
        self.selection_features: list[float] | None = None
        self.selection_eligible: list[str] = []
        self.selected_fallbacks = 0

    def __call__(self, obs: Any, configuration: Any = None):
        step = int(_get(obs, "step", 0) or 0)
        if step == 0 or step < self.last_step:
            self._reset()
        self.last_step = step
        actions: dict[str, dict[str, Any]] = {}
        for model_id, expert in self.experts.items():
            try:
                actions[model_id] = _copy_action(expert(obs, configuration))
            except Exception as exc:
                self.prefix_errors[model_id].append(f"step={step}:{type(exc).__name__}:{exc}")
        anchor_action = actions.get(self.anchor)
        if anchor_action is None:
            # A broken anchor is never hidden by another expert.  This explicit
            # pass action makes the safety failure visible in DONE/reward logs.
            return {"farmer": ["PASS"], "hands": [], "market": []}

        if step < self.switch_step:
            self.seen_prefix_steps.add(step)
            anchor_bytes = _action_bytes(anchor_action)
            for model_id in self.experts:
                action = actions.get(model_id)
                if action is None:
                    self.prefix_match[model_id] = False
                    if self.prefix_first_mismatch[model_id] is None:
                        self.prefix_first_mismatch[model_id] = step
                    continue
                encoded = _action_bytes(action)
                self.prefix_hashes[model_id].update(encoded)
                if encoded != anchor_bytes:
                    self.prefix_match[model_id] = False
                    if self.prefix_first_mismatch[model_id] is None:
                        self.prefix_first_mismatch[model_id] = step
            return anchor_action

        if self.selected is None:
            complete = self.seen_prefix_steps == set(range(self.switch_step))
            eligible = [
                model_id for model_id in self.experts
                if complete and self.prefix_match[model_id] and not self.prefix_errors[model_id] and model_id in actions
            ]
            if not eligible:
                eligible = [self.anchor]
                self.selection_reason = "incomplete_or_incompatible_prefix"
            try:
                self.selection_features = public_features(obs).astype(float).tolist()
                self.selected = str(self.selector.choose(obs, eligible))
                if self.selected not in eligible:
                    raise ValueError("selector returned an ineligible expert")
                self.selection_reason = getattr(self.selector, "last_reason", self.selection_reason)
            except Exception as exc:
                self.selected = self.anchor
                self.selection_reason = f"selector_fallback:{type(exc).__name__}:{exc}"
            self.selection_eligible = list(eligible)

        selected_action = actions.get(self.selected)
        if selected_action is None:
            self.selected_fallbacks += 1
            return anchor_action
        return selected_action

    def diagnostics(self) -> dict[str, Any]:
        selector_scores = getattr(self.selector, "last_scores", {})
        return {
            "kind": "shadow_full_expert_router",
            "switch_step": self.switch_step,
            "anchor": self.anchor,
            "selected": self.selected,
            "selection_reason": self.selection_reason,
            "selection_eligible": list(self.selection_eligible),
            "selection_features": self.selection_features,
            "selector_scores": dict(selector_scores),
            "prefix_complete": self.seen_prefix_steps == set(range(self.switch_step)),
            "prefix_match": dict(self.prefix_match),
            "prefix_first_mismatch": dict(self.prefix_first_mismatch),
            "prefix_errors": {key: list(value) for key, value in self.prefix_errors.items()},
            "prefix_hash": {key: value.hexdigest() for key, value in self.prefix_hashes.items()},
            "selected_fallbacks": self.selected_fallbacks,
        }


def create_router(registry: Registry, spec: Mapping[str, Any], stack: tuple[str, ...] = ()) -> ShadowRouter:
    model_id = str(spec.get("id") or "router")
    expert_ids = [str(item) for item in (spec.get("experts") or [])]
    if len(expert_ids) < 2:
        raise ValueError(f"router {model_id} needs at least two complete experts")
    anchor = str(spec.get("anchor") or expert_ids[0])
    experts = {item: create_agent(registry, item, _stack=stack) for item in expert_ids}
    expert_specs = {item: registry.require(item) for item in expert_ids}
    kind = str(spec.get("router_kind") or "rule")
    if kind == "rule":
        selector: RuleSelector | LearnedSelector = RuleSelector(spec, expert_specs, anchor)
    elif kind == "learned":
        weights = spec.get("weights")
        if not weights:
            raise ValueError(f"learned router {model_id} has no weights")
        selector = LearnedSelector(resolve_path(registry, weights), anchor)
    else:
        raise ValueError(f"unknown router kind: {kind}")
    return ShadowRouter(model_id, experts, expert_specs, anchor, selector, int(spec.get("switch_step", 72)))
