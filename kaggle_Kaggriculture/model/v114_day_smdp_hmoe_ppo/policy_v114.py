"""V114 stable product-expert policy; no historical-agent action fallback."""

from __future__ import annotations

from pathlib import Path
import sys

from flax import serialization
import numpy as np


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

from policy_sequence_action import TimedSequenceActionV113Policy  # noqa: E402
import action_space as space  # noqa: E402


def reserve_shadow(shadow: dict, cash_reserve: float) -> dict:
    """Return a detached market projection with spendable cash above reserve."""
    projected = dict(shadow)
    projected["money"] = max(0.0, float(shadow.get("money", 0.0)) - float(cash_reserve))
    return projected


def observation_step(obs) -> int:
    """Canonical official step; Kaggriculture observations expose day/hour."""
    explicit = space.get(obs, "step", None)
    if explicit is not None:
        return int(explicit)
    return 24 * int(space.get(obs, "day", 0) or 0) + int(space.get(obs, "hour", 0) or 0)


def with_observation_step(obs):
    """Add the derived step without mutating the official observation object."""
    if space.get(obs, "step", None) is not None:
        return obs
    enriched = dict(obs)
    enriched["step"] = observation_step(obs)
    return enriched


class V114StableExpertPolicy(TimedSequenceActionV113Policy):
    """Fixed production/market expert composition used before Manager training."""

    def __init__(
        self, checkpoint: Path, unit_expert: int, market_expert: int, *,
        cash_reserve: float = 0.0, worker_cap: int | None = None,
        terminal_buy_cutoff: int | None = None,
    ):
        payload = serialization.msgpack_restore(Path(checkpoint).read_bytes())
        if not str(payload.get("model_id", "")).startswith("v114_"):
            raise ValueError("checkpoint is not registered to V114")
        if payload.get("inherits_v113_checkpoint") is not False:
            raise ValueError("V114 may not inherit a V113 checkpoint")
        if cash_reserve < 0:
            raise ValueError("cash_reserve must be non-negative")
        if terminal_buy_cutoff is not None and terminal_buy_cutoff < 0:
            raise ValueError("terminal_buy_cutoff must be non-negative")
        self.cash_reserve = float(cash_reserve)
        self.terminal_buy_cutoff = terminal_buy_cutoff
        super().__init__(
            checkpoint,
            forced_unit_expert=int(unit_expert),
            forced_market_expert=int(market_expert),
            router_period=24,
            scale_worker_cap=worker_cap,
        )

    def _market_legal_mask(self, obs, shadow):
        legal = np.asarray(super()._market_legal_mask(obs, reserve_shadow(shadow, self.cash_reserve)))
        step = observation_step(obs)
        if self.terminal_buy_cutoff is not None and step >= self.terminal_buy_cutoff:
            for index, name in enumerate(space.MARKET_TOKENS):
                if name == "HIRE" or name == "BUY_LAND" or name.startswith("BUY_"):
                    legal[index] = False
        legal[space.MARKET_INDEX["STOP"]] = True
        return legal

    def _market_quantity_mask(self, obs, shadow, token):
        name = space.MARKET_TOKENS[int(token)]
        if name.startswith("SELL:"):
            return super()._market_quantity_mask(obs, shadow, token)
        return super()._market_quantity_mask(obs, reserve_shadow(shadow, self.cash_reserve), token)

    def act(self, obs):
        return super().act(with_observation_step(obs))

    def sample(self, obs, *args, **kwargs):
        return super().sample(with_observation_step(obs), *args, **kwargs)
