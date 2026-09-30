"""Build isolated opponent policies for V113 evaluation and self-play."""

from __future__ import annotations

from pathlib import Path

from policy_factorized import FactorizedV113Policy
from policy_history_sequence import HistoryTimedSequenceActionV113Policy
from policy_sequence_action import SequenceActionV113Policy, TimedSequenceActionV113Policy


def checkpoint_opponent(
    checkpoint: Path,
    architecture: str,
    forced_unit_expert: int | None,
    forced_market_expert: int | None,
    unit_expert_schedule=None,
    market_expert_schedule=None,
):
    policy_classes = {
        "factorized": FactorizedV113Policy,
        "sequence": SequenceActionV113Policy,
        "timed-sequence": TimedSequenceActionV113Policy,
        "history-timed-sequence": HistoryTimedSequenceActionV113Policy,
    }
    try:
        policy_class = policy_classes[architecture]
    except KeyError as exc:
        raise ValueError(f"unsupported checkpoint opponent architecture: {architecture}") from exc
    return policy_class(
        checkpoint,
        forced_unit_expert=forced_unit_expert,
        forced_market_expert=forced_market_expert,
        unit_expert_schedule=unit_expert_schedule,
        market_expert_schedule=market_expert_schedule,
    )
