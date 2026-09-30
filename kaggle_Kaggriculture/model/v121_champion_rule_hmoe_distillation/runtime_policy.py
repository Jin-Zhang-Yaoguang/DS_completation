"""纯 Python 规则树推理；当前只输出分层合同，不直接产生游戏 action。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


MODEL_PATH = Path(__file__).resolve().with_name("rule_hmoe_model.json")


def _walk(node: dict, features: Mapping[str, float]):
    while "feature" in node:
        value = float(features.get(str(node["feature"]), 0.0))
        node = node["left"] if value <= float(node["threshold"]) else node["right"]
    return node


class RuleHMoE:
    def __init__(self, model: dict | None = None) -> None:
        self.model = model or json.loads(MODEL_PATH.read_text(encoding="utf-8"))
        contract = self.model["runtime_contract"]
        if contract.get("tape") or contract.get("step_action_lookup"):
            raise ValueError("V121 禁止 tape serving")

    def decide(self, features: Mapping[str, float]) -> dict:
        macro = str(_walk(self.model["macro_router"]["root"], features)["leaf"])
        daily_features = dict(features)
        for expert in self.model["macro_router"]["classes"]:
            daily_features[f"macro_{expert}"] = float(expert == macro)
        daily = str(_walk(self.model["daily_router"]["root"], daily_features)["leaf"])
        market = dict(_walk(self.model["global_market"]["root"], features)["value"])
        prototype = dict(self.model["expert_contract_prototypes"].get(daily, {}))
        return {
            "macro_expert": macro,
            "daily_expert": daily,
            "daily_contract": prototype,
            "market_forecast": market,
        }


def model_status() -> dict:
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    return {
        "schema": model["schema"],
        "status": model["status"],
        "primary_action_source": model["runtime_contract"]["primary_action_source"],
        "tape": model["runtime_contract"]["tape"],
    }

