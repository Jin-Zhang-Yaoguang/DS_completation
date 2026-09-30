"""V121 闭环 HMoE：当前状态路由，专家树直接生成动作。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import joblib
import json
import os

from behavior_features import actor_features, decode_market, global_features, legalize_unit, positions
from runtime_policy import RuleHMoE


HERE = Path(__file__).resolve().parent
_BUNDLE = joblib.load(HERE / "behavior_hmoe.joblib")
_ROUTER = RuleHMoE()
_STATE = {0: {"last_step": -1, "prices": {}}, 1: {"last_step": -1, "prices": {}}}


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _seat(obs: Mapping[str, Any]) -> int:
    return 1 if _integer(obs.get("player")) == 1 else 0


def _step(obs: Mapping[str, Any]) -> int:
    return _integer(obs.get("day")) * 24 + _integer(obs.get("hour"))


def _features(obs: Mapping[str, Any]) -> dict[str, float]:
    features = global_features(obs)
    seat, step = _seat(obs), _step(obs)
    state = _STATE[seat]
    prices = dict((obs.get("market") or {}).get("prices") or {})
    if step == 0 or step <= _integer(state.get("last_step"), -1):
        state["prices"] = prices
    previous = dict(state.get("prices") or {})
    for item, price in prices.items():
        features[f"price_delta_{item}"] = float(_integer(price) - _integer(previous.get(item), _integer(price)))
    state["last_step"], state["prices"] = step, prices
    return features


def _vector(features: Mapping[str, float], names: list[str]) -> list[float]:
    return [float(features.get(name, 0.0)) for name in names]


def _empty(obs: Mapping[str, Any]) -> dict:
    farms = list(obs.get("farms") or [{}, {}])
    farm = farms[_seat(obs)] if len(farms) > _seat(obs) else {}
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in list(farm.get("hands") or [])], "market": []}


def agent(obs, configuration=None):
    try:
        shared = _features(obs)
        routed_expert = str(_ROUTER.decide(shared)["daily_expert"])
        teacher = os.environ.get("V121_TEACHER", "tetsuya")
        use_teacher = teacher in _BUNDLE.get("teacher_unit_models", {})
        expert = routed_expert if routed_expert in _BUNDLE["unit_models"] else "CROP"
        seat = _seat(obs)
        farms = list(obs.get("farms") or [{}, {}])
        farm = farms[seat]
        count = len(positions(farm))
        unit_actions = []
        model = _BUNDLE["teacher_unit_models"][teacher] if use_teacher else _BUNDLE["unit_models"][expert]
        quantities = _BUNDLE["teacher_quantity_medians"][teacher] if use_teacher else _BUNDLE["quantity_medians"][expert]
        for actor in range(count):
            feature = actor_features(obs, actor)
            # 路由所需的价格变化也进入动作树；训练 schema 中不存在的字段会被忽略。
            feature.update({key: value for key, value in shared.items() if key.startswith("price_delta_")})
            label = str(model.predict([_vector(feature, _BUNDLE["actor_features"])])[0])
            unit_actions.append(legalize_unit(label, quantities.get(label, 1), obs, actor))
        if use_teacher:
            raw = _BUNDLE["teacher_market_models"][teacher].predict(
                [_vector(shared, _BUNDLE["teacher_market_features"])]
            )[0]
            market = list(json.loads(str(raw)))[:10]
        else:
            market_values = _BUNDLE["market_models"][expert].predict(
                [_vector(shared, _BUNDLE["global_features"])]
            )[0]
            market = decode_market(list(market_values), _BUNDLE["market_targets"], obs)
        return {"farmer": unit_actions[0], "hands": unit_actions[1:], "market": market}
    except Exception:
        return _empty(obs)


def model_status() -> dict:
    return {
        "schema": _BUNDLE["schema"],
        "primary_action_source": _BUNDLE["runtime_contract"]["primary_action_source"],
        "tape": False,
        "step_action_lookup": False,
    }
