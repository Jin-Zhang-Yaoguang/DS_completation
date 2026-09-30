"""Build duration-aware V114 SMDP transitions from an online episode stream."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from smdp_schema import EpisodeTrajectory, ManagerDecision, SMDPTransition


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def visible_summary(obs: Any) -> tuple[float, ...]:
    """Small leakage-safe summary used by the rollout contract tests.

    Production training may replace it with the fixed-shape encoder, but the
    information boundary remains identical: own private plus public opponent.
    """
    player = 1 if int(_get(obs, "player", 0) or 0) == 1 else 0
    farms = list(_get(obs, "farms", []) or [])
    own = farms[player] if player < len(farms) else {}
    opponent = farms[1 - player] if len(farms) > 1 else {}
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    market = _get(obs, "market", {}) or {}
    inventory = _get(market, "inventory", {}) or {}
    return (
        float(_get(obs, "step", 0) or 0) / 719.0,
        float(_get(own, "money", 0) or 0),
        float(_get(opponent, "money", 0) or 0),
        float(len(_get(own, "hands", []) or [])),
        float(len(_get(opponent, "hands", []) or [])),
        float(sum(float(v or 0) for v in shed.values())),
        float(sum(float(v or 0) for v in inventory.values())),
    )


@dataclass
class _OpenTransition:
    start_step: int
    decision: ManagerDecision
    start_features: tuple[float, ...]
    residual_non_keep: int = 0
    contract_violations: tuple[str, ...] = ()


class SMDPRolloutBuilder:
    """Stateful builder that closes transitions only at option boundaries."""

    def __init__(self, episode_id: str, seed: int, seat: int, opponent_id: str, opponent_layer: str) -> None:
        self.trajectory = EpisodeTrajectory(episode_id, int(seed), int(seat), opponent_id)
        self.opponent_layer = opponent_layer
        self._open: _OpenTransition | None = None

    def begin(self, obs: Any, decision: ManagerDecision) -> None:
        if self._open is not None:
            raise RuntimeError("previous option transition is still open")
        step = int(_get(obs, "step", 0) or 0)
        self._open = _OpenTransition(step, decision, visible_summary(obs))

    def record_residual(self, non_keep: bool, violations: Sequence[str] = ()) -> None:
        if self._open is None:
            raise RuntimeError("no open transition")
        count = self._open.residual_non_keep + int(bool(non_keep))
        if count > 4:
            raise ValueError("daily residual non-KEEP budget exceeded")
        self._open.residual_non_keep = count
        self._open.contract_violations = tuple((*self._open.contract_violations, *map(str, violations)))

    def close(
        self,
        obs: Any,
        *,
        reward: float,
        own_reward: float,
        opponent_reward: float,
        catastrophe_cost: float,
        terminal: bool,
    ) -> SMDPTransition:
        if self._open is None:
            raise RuntimeError("no open transition")
        end_step = int(_get(obs, "step", 0) or 0)
        if terminal and end_step == self._open.start_step:
            end_step += 1
        row = SMDPTransition(
            episode_id=self.trajectory.episode_id,
            seed=self.trajectory.seed,
            seat=self.trajectory.seat,
            opponent_id=self.trajectory.opponent_id,
            opponent_layer=self.opponent_layer,
            start_step=self._open.start_step,
            end_step=end_step,
            decision=self._open.decision,
            reward=reward,
            own_reward=own_reward,
            opponent_reward=opponent_reward,
            catastrophe_cost=catastrophe_cost,
            terminal=terminal,
            start_features=self._open.start_features,
            end_features=visible_summary(obs),
            residual_non_keep=self._open.residual_non_keep,
            contract_violations=self._open.contract_violations,
        )
        self.trajectory.append(row)
        self._open = None
        return row

