"""V114 serving contract for one independently trained lineage foundation policy.

The neural action generator is loaded from a V114 checkpoint and receives only
the public observation plus deterministic history of this policy's own executed
actions.  Historical teachers are never imported or called at serving time.
"""

from __future__ import annotations

from pathlib import Path
import sys

from flax import serialization


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

from policy_history_sequence import HistoryTimedSequenceActionV113Policy  # noqa: E402


REPLAY_UNIT_PHASE_SCHEDULE = ((0, 4), (72, 2), (216, 0), (480, 1), (671, 5))
REPLAY_MARKET_PHASE_SCHEDULE = ((0, 4), (480, 3), (671, 5))


class LineagePhaseV114Policy(HistoryTimedSequenceActionV113Policy):
    """Legal-mask executor around a from-scratch V114 lineage checkpoint."""

    def __init__(self, checkpoint: Path, *args, **kwargs):
        payload = serialization.msgpack_restore(Path(checkpoint).read_bytes())
        if payload.get("strategy_parent") is not None:
            raise ValueError("lineage foundation checkpoint must have strategy_parent=null")
        if payload.get("inherits_v113_checkpoint") is not False:
            raise ValueError("lineage foundation checkpoint must be trained from scratch")
        if payload.get("online_historical_agent_fallback") is not False:
            raise ValueError("historical agent fallback is forbidden")
        if not str(payload.get("architecture", "")).startswith("v114-history32-timed-"):
            raise ValueError("checkpoint is not a registered V114 lineage phase policy")
        self.lineage_id = str(payload.get("lineage_id", ""))
        self.teacher_family_evidence = str(payload.get("teacher_family_evidence", ""))
        if self.lineage_id in {"V11A_V2_REPLAY", "V11B_V8_REPLAY"}:
            # V11's expert targets are a causal, pre-action time-phase contract.
            # Allowing a free per-step argmax at serving time is a train/deploy
            # mismatch: one distribution-shifted state can keep the procurement
            # expert active through the liquidation phase.  The higher-level
            # Manager remains the trainable Router; this foundation executor
            # deterministically enforces its registered low-level phases.
            kwargs.setdefault("unit_expert_schedule", REPLAY_UNIT_PHASE_SCHEDULE)
            kwargs.setdefault("market_expert_schedule", REPLAY_MARKET_PHASE_SCHEDULE)
        self.action_steps = 0
        super().__init__(checkpoint, *args, **kwargs)

    def act(self, obs):
        step = int(obs.get("step", 0) or 0)
        if step <= self.last_step:
            self.action_steps = 0
        action = super().act(obs)
        self.action_steps += 1
        return action


def make_agent(checkpoint: Path):
    policy = LineagePhaseV114Policy(checkpoint)
    return lambda obs, configuration=None: policy(obs, configuration)
