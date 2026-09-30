"""Kaggle serving entry for V31 V21-shadow SELL queue best response."""

from __future__ import annotations

from typing import Any

import queue_core as core


MODEL_ID = "v31_v21_shadow_queue_br"
DEFAULT_CONFIGURATION = {
    "actTimeout": 1,
    "boardSize": 10,
    "episodeSteps": 720,
    "startingMoney": 3000,
    "maxMarketOrdersPerTurn": 10,
    "turnsPerDay": 24,
    "shedCapacity": 100,
    "weedSpawnChance": 0.005,
    "townShopUnlockInterval": 3,
    "townShopSellInterval": 4,
    "townCenterSellInterval": 24,
    "farmHandCostMult": 1,
    "marketParams": {},
}


class V31Agent(core.QueueBestResponseAgent):
    def __init__(self) -> None:
        super().__init__(
            max_clone_distance=10**9,
            start_step=217,
            minimum_conformance_steps=216,
            require_public_mirror=False,
        )

    def diagnostics(self) -> dict[str, Any]:
        payload = super().diagnostics()
        payload["kind"] = MODEL_ID
        payload["model_id"] = MODEL_ID
        payload["parent"] = "v21_top_meta_moe"
        payload["mechanism"] = "exact_v21_shadow_sell_queue_best_response"
        return payload


def make_agent() -> V31Agent:
    return V31Agent()


_AGENT: V31Agent | None = None


def model_status() -> dict[str, Any]:
    if _AGENT is None:
        return {"kind": MODEL_ID, "model_id": MODEL_ID, "status": "not_started"}
    return _AGENT.diagnostics()


def agent(obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
    global _AGENT
    step = int(core._get(obs, "step", 0) or 0)
    if _AGENT is None or step == 0 or step < _AGENT.last_step:
        _AGENT = make_agent()
    return _AGENT(obs, configuration or DEFAULT_CONFIGURATION)
