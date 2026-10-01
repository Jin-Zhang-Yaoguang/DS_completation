#!/usr/bin/env python3
"""Live two-seat arena with a fixed, progressively visible shop scenario."""

from __future__ import annotations

import copy
import importlib.util
import sysconfig
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable


HERE = Path(__file__).resolve().parent
BUILD_DIR = HERE / "build"
VALID_SHOPS = frozenset({
    "BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP",
    "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE",
})
PASS_ACTION = {"farmer": ["PASS"], "hands": [], "market": []}
Agent = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ShopReveal:
    shop: str
    visible_from_step: int


@dataclass
class ScenarioResult:
    rewards: tuple[float, float]
    steps: int
    trace: list[dict[str, Any]]


def load_scenario_module() -> Any:
    suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    matches = sorted(BUILD_DIR.glob(f"kagsim_scenario*{suffix}"))
    if len(matches) != 1:
        raise RuntimeError("build kagsim_scenario first with build_scenario.py")
    spec = importlib.util.spec_from_file_location("kagsim_scenario", matches[0])
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {matches[0]}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_schedule(schedule: Iterable[ShopReveal | dict[str, Any] | tuple[str, int]]) \
        -> tuple[ShopReveal, ...]:
    rows: list[ShopReveal] = []
    for raw in schedule:
        if isinstance(raw, ShopReveal):
            row = raw
        elif isinstance(raw, dict):
            row = ShopReveal(str(raw["shop"]), int(raw["visible_from_step"]))
        else:
            shop, step = raw
            row = ShopReveal(str(shop), int(step))
        if row.shop not in VALID_SHOPS:
            raise ValueError(f"unknown shop {row.shop!r}")
        if row.visible_from_step < 0:
            raise ValueError("visible_from_step must be nonnegative")
        rows.append(row)
    if len(rows) > 10:
        raise ValueError("scenario exceeds engine MAX_SHOP_INSTANCES=10")
    if any(rows[index].visible_from_step < rows[index - 1].visible_from_step
           for index in range(1, len(rows))):
        raise ValueError("schedule must be ordered by nondecreasing visible_from_step")
    return tuple(rows)


class ScenarioRunner:
    """Advance both agents live; reveal only the current shop prefix.

    Agents receive only their current observation.  Neither a schedule nor a
    future-shop accessor is passed into either callable.
    """

    def __init__(self, seed: int, agent_a: Agent, agent_b: Agent,
                 schedule: Iterable[ShopReveal | dict[str, Any] | tuple[str, int]] = (),
                 steps: int = 720, module: Any | None = None) -> None:
        self.module = module or load_scenario_module()
        if getattr(self.module, "ENGINE_VERSION", None) != "1.32.7":
            raise RuntimeError(f"unexpected engine {getattr(self.module, 'ENGINE_VERSION', None)!r}")
        self.schedule = normalize_schedule(schedule)
        self.agent_a = agent_a
        self.agent_b = agent_b
        self.game = self.module.Game(int(seed), int(steps))
        self._scenario_active = bool(self.schedule)
        if self._scenario_active:
            self.game.force_shops(self.visible_prefix(0))

    @property
    def step_count(self) -> int:
        return int(self.game.step_count)

    def visible_prefix(self, step: int | None = None) -> list[str]:
        now = self.step_count if step is None else int(step)
        return [row.shop for row in self.schedule if row.visible_from_step <= now]

    def observations(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return self.game.observe(0), self.game.observe(1)

    def step_once(self, record: bool = False) -> dict[str, Any]:
        if self.game.done:
            raise RuntimeError("scenario is already done")
        before = self.step_count
        obs_a, obs_b = self.observations()
        # Each callable receives only its current seat observation.  Defensive
        # copies stop accidental cross-agent mutation in Python code.
        action_a = self.agent_a(copy.deepcopy(obs_a))
        action_b = self.agent_b(copy.deepcopy(obs_b))
        self.game.step(action_a, action_b)
        if self._scenario_active:
            # Required ordering: force the now-visible prefix only after the
            # shared engine step and before either next observation.
            self.game.force_shops(self.visible_prefix(self.step_count))
        row = {
            "step": before,
            "next_step": self.step_count,
            "visible_shops": list(obs_a["town"]["unlocked_shops"]),
            "rewards": (float(self.game.reward(0)), float(self.game.reward(1))),
        }
        if record:
            row.update({"obs_a": obs_a, "obs_b": obs_b,
                        "action_a": action_a, "action_b": action_b})
        return row

    def run(self, record: bool = False) -> ScenarioResult:
        trace: list[dict[str, Any]] = []
        while not self.game.done:
            row = self.step_once(record=record)
            if record:
                trace.append(row)
        return ScenarioResult(
            rewards=(float(self.game.reward(0)), float(self.game.reward(1))),
            steps=self.step_count,
            trace=trace,
        )


def pass_agent(obs: dict[str, Any]) -> dict[str, Any]:
    hands = [["PASS"] for _ in list((obs.get("farms") or [{}, {}])
                                      [int(obs.get("player", 0))]
                                      .get("hands", []) or [])]
    return {"farmer": ["PASS"], "hands": hands, "market": []}


def run_scenario(seed: int, agent_a: Agent, agent_b: Agent,
                 schedule: Iterable[ShopReveal | dict[str, Any] | tuple[str, int]] = (),
                 steps: int = 720, record: bool = False) -> ScenarioResult:
    return ScenarioRunner(seed, agent_a, agent_b, schedule, steps).run(record=record)


__all__ = [
    "Agent", "PASS_ACTION", "ScenarioResult", "ScenarioRunner", "ShopReveal",
    "load_scenario_module", "normalize_schedule", "pass_agent", "run_scenario",
]
