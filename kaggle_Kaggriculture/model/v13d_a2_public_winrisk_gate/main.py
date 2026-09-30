"""V13D: protect a strict public-money lead by bypassing A2 throttling."""

from __future__ import annotations

import copy
import math
from typing import Any, Mapping

try:  # Standalone Kaggle archive.
    import a2_agent as a2  # type: ignore
except ImportError:  # Repository development runtime.
    from kaggle_Kaggriculture.model.v12a2_no_shop_gate import main as a2


MODEL_ID = "v13d_a2_public_winrisk_gate"
_MISSING = object()


def _strict_public_money(obs: Any) -> tuple[float, float] | None:
    """Return seat-correct public money, or None on any missing/invalid field."""

    player = a2.base._get(obs, "player", _MISSING)
    farms = a2.base._get(obs, "farms", _MISSING)
    if player is _MISSING or farms is _MISSING:
        return None
    # bool is an int subclass in Python, but neither True/False is a valid
    # serialized seat or public-money value for this fail-closed gate.
    if isinstance(player, bool):
        return None
    try:
        seat = int(player)
        farm_list = list(farms)
    except (TypeError, ValueError):
        return None
    if seat not in (0, 1) or len(farm_list) != 2:
        return None
    own_raw = a2.base._get(farm_list[seat], "money", _MISSING)
    opponent_raw = a2.base._get(farm_list[1 - seat], "money", _MISSING)
    if own_raw is _MISSING or opponent_raw is _MISSING:
        return None
    if isinstance(own_raw, bool) or isinstance(opponent_raw, bool):
        return None
    try:
        own = float(own_raw)
        opponent = float(opponent_raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(own) or not math.isfinite(opponent):
        return None
    return own, opponent


class A2PublicWinRiskAgent(a2.NoShopGateAgent):
    """Bypass an eligible A2 throttle only while strictly leading publicly."""

    def _reset(self) -> None:
        super()._reset()
        self.lead_bypass_steps = 0
        self.unknown_public_bank_steps = 0
        self.a2_throttle_eligible_steps = 0

    def _should_throttle(
        self, obs: Any, action: Mapping[str, Any], branch: str | None
    ) -> tuple[bool, str, frozenset[str]]:
        a2_decision = super()._should_throttle(obs, action, branch)
        try:
            throttle, _, _ = a2_decision
            if not throttle:
                return a2_decision
            self.a2_throttle_eligible_steps += 1
            money = _strict_public_money(obs)
            if money is None:
                self.unknown_public_bank_steps += 1
                return a2_decision
            own, opponent = money
            if own > opponent:
                self.lead_bypass_steps += 1
                return False, "v13d_strict_public_lead_bypass", frozenset()
            return a2_decision
        except Exception:
            # Missing or malformed V13-only evidence must never relax A2.
            return a2_decision

    def diagnostics(self) -> dict[str, Any]:
        payload = copy.deepcopy(super().diagnostics())
        payload.update(
            {
                "kind": "v13d_a2_public_winrisk_gate",
                "model_id": MODEL_ID,
                "parent_id": "v12a2_no_shop_gate",
                "change_scope": "bypass eligible A2 throttle only on strict public-money lead",
                "lead_bypass_steps": self.lead_bypass_steps,
                "unknown_public_bank_steps": self.unknown_public_bank_steps,
                "a2_throttle_eligible_steps": self.a2_throttle_eligible_steps,
            }
        )
        return payload


def make_agent() -> A2PublicWinRiskAgent:
    return A2PublicWinRiskAgent()


_AGENT: A2PublicWinRiskAgent | None = None


def model_status() -> dict[str, Any]:
    if _AGENT is None:
        return {"kind": MODEL_ID, "model_id": MODEL_ID, "status": "not_started"}
    return _AGENT.diagnostics()


def agent(obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
    global _AGENT
    step = a2.base._step(obs)
    if _AGENT is None or step == 0 or step < _AGENT.last_step:
        _AGENT = make_agent()
    return _AGENT(obs, configuration)
