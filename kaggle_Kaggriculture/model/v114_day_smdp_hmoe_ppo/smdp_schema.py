"""Typed, duration-aware trajectory contract for V114."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Iterable, Mapping


def _finite(value: float, name: str) -> float:
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"{name} must be finite")
    return value


@dataclass(frozen=True)
class ManagerDecision:
    option_id: str
    budget_tier: str
    risk_tier: str


@dataclass(frozen=True)
class SMDPTransition:
    episode_id: str
    seed: int
    seat: int
    opponent_id: str
    opponent_layer: str
    start_step: int
    end_step: int
    decision: ManagerDecision
    reward: float
    own_reward: float
    opponent_reward: float
    catastrophe_cost: float
    terminal: bool
    start_features: tuple[float, ...] = field(default_factory=tuple)
    end_features: tuple[float, ...] = field(default_factory=tuple)
    residual_non_keep: int = 0
    contract_violations: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.seat not in (0, 1):
            raise ValueError("seat must be 0 or 1")
        if self.end_step <= self.start_step:
            raise ValueError("end_step must be greater than start_step")
        if self.residual_non_keep < 0 or self.residual_non_keep > 4:
            raise ValueError("residual_non_keep must be in 0..4")
        _finite(self.reward, "reward")
        _finite(self.own_reward, "own_reward")
        _finite(self.opponent_reward, "opponent_reward")
        _finite(self.catastrophe_cost, "catastrophe_cost")

    @property
    def duration_turns(self) -> int:
        return self.end_step - self.start_step

    def discount(self, gamma_day: float = 0.99) -> float:
        gamma_day = _finite(gamma_day, "gamma_day")
        if not 0.0 < gamma_day <= 1.0:
            raise ValueError("gamma_day must be in (0, 1]")
        return gamma_day ** (self.duration_turns / 24.0)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EpisodeTrajectory:
    episode_id: str
    seed: int
    seat: int
    opponent_id: str
    transitions: list[SMDPTransition] = field(default_factory=list)

    def append(self, transition: SMDPTransition) -> None:
        if transition.episode_id != self.episode_id or transition.seed != self.seed:
            raise ValueError("transition episode identity mismatch")
        if transition.seat != self.seat or transition.opponent_id != self.opponent_id:
            raise ValueError("transition matchup identity mismatch")
        if self.transitions and transition.start_step != self.transitions[-1].end_step:
            raise ValueError("transitions must be contiguous")
        self.transitions.append(transition)

    def validate_complete(self, expected_end_step: int = 719) -> None:
        if not self.transitions:
            raise ValueError("trajectory is empty")
        if self.transitions[0].start_step != 0:
            raise ValueError("trajectory must start at step 0")
        if self.transitions[-1].end_step != expected_end_step:
            raise ValueError("trajectory has incomplete horizon")
        if not self.transitions[-1].terminal:
            raise ValueError("last transition must be terminal")

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "seed": self.seed,
            "seat": self.seat,
            "opponent_id": self.opponent_id,
            "transitions": [row.to_dict() for row in self.transitions],
        }


def seed_block_id(seed: int, opponent_id: str) -> str:
    payload = f"{int(seed)}|{opponent_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def paired_seat_contract(rows: Iterable[Mapping[str, Any]]) -> None:
    blocks: dict[tuple[int, str], set[int]] = {}
    for row in rows:
        key = (int(row["seed"]), str(row["opponent_id"]))
        blocks.setdefault(key, set()).add(int(row["seat"]))
    invalid = {key: sorted(seats) for key, seats in blocks.items() if seats != {0, 1}}
    if invalid:
        printable = {f"{seed}|{opponent}": seats for (seed, opponent), seats in invalid.items()}
        raise ValueError(f"same seed/opponent must contain both seats: {json.dumps(printable)}")
