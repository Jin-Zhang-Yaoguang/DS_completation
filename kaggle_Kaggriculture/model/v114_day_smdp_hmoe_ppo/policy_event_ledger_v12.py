"""V12 engineering policy: persistent unit tasks plus event transaction ledger."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from event_ledger import EventKind, MarketEvent, TransactionIntent
from event_ledger_controller import EventLedgerController, economy_snapshot
from persistent_unit_tasks import PersistentUnitTaskExecutor, UnitTaskBCPolicy
from policy_event_market_hmoe import LearnedEventMarketPolicy


PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
PRICES = {
    "WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120,
    "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200,
    "FERTILIZER": 100, "COW": 500, "SHEEP": 300,
}
SEED_COST = {"WHEAT": 10, "MELON": 80}


class BootstrapEventMarketPolicy:
    """Explicit non-qualifying scaffold used only to expose unit-task failures."""

    qualification_status = "BOOTSTRAP_ONLY_NOT_EVENT_EXPERT_NOT_PPO_NOT_GOLD"

    def __call__(
        self, observation: Mapping[str, Any], event: MarketEvent
    ) -> list[TransactionIntent]:
        state = economy_snapshot(observation)
        day = state.step // 24
        intents: list[TransactionIntent] = []
        # Realize inventory at every authorized event before new commitments.
        for product in PRODUCTS:
            if int(state.inventory.get(product, 0)) > 0:
                intents.append(TransactionIntent(
                    "SELL", product, 100, 0, 0, 0, state.step, retain_total=0
                ))
        if event.kind == EventKind.TERMINAL_WINDOW or day >= 27:
            return intents
        intents.extend((
            TransactionIntent(
                "HIRE", None, 16, 1, 100, 0, state.step,
                target_total=6, worker_cap=6,
            ),
            TransactionIntent(
                "BUY_SEED", "WHEAT", 100, SEED_COST["WHEAT"], 300, 0,
                state.step, target_total=20,
            ),
            TransactionIntent(
                "BUY_SEED", "MELON", 100, SEED_COST["MELON"], 960, 0,
                state.step, target_total=12,
            ),
            TransactionIntent(
                "BUY_PRODUCT", "WHEAT", 100, PRICES["WHEAT"], 300, 0,
                state.step, target_total=6,
            ),
        ))
        if day == 0:
            intents.extend((
                TransactionIntent(
                    "BUY_ANIMAL", "COW", 4, PRICES["COW"], 1000, 0,
                    state.step, target_total=2, animal_cap=2,
                ),
                TransactionIntent(
                    "BUY_ANIMAL", "SHEEP", 4, PRICES["SHEEP"], 600, 0,
                    state.step, target_total=2, animal_cap=2,
                ),
            ))
        return intents


class EventLedgerV12EngineeringPolicy:
    """Engineering-only composition; not a foundation candidate or PPO model."""

    def __init__(
        self,
        unit_checkpoint: Path,
        market_checkpoint: Path | None = None,
        contract: str | None = None,
    ):
        self.contract = contract
        self.unit_planner = UnitTaskBCPolicy(unit_checkpoint, contract=contract)
        self.unit_executor = PersistentUnitTaskExecutor(self.unit_planner)
        self.market_policy = (
            LearnedEventMarketPolicy(market_checkpoint, contract=contract)
            if market_checkpoint is not None else BootstrapEventMarketPolicy()
        )
        self.controller = EventLedgerController(
            self.unit_executor.act, self.market_policy
        )
        self.action_steps = 0

    def act(self, observation: Mapping[str, Any]) -> dict:
        step = int(observation.get("step", 0) or 0)
        if step < self.controller.last_step or (step == 0 and self.controller.last_step > 0):
            self.unit_executor.reset()
            self.controller.reset()
            self.action_steps = 0
        action = self.controller.act(observation)
        self.action_steps += 1
        return action

    def __call__(self, observation, configuration=None):
        return self.act(observation)

    def audit(self) -> dict:
        return {
            "action_steps": self.action_steps,
            "enterprise_contract": self.contract,
            "unit": self.unit_executor.audit(),
            "events": self.controller.audit(),
            "market": (
                self.market_policy.audit()
                if hasattr(self.market_policy, "audit") else {
                    "qualification_status": self.market_policy.qualification_status
                }
            ),
            "qualification_status": "ENGINEERING_ONLY_NOT_FOUNDATION_NOT_PPO_NOT_GOLD",
        }


def make_agent(
    checkpoint: Path,
    market_checkpoint: Path | None = None,
    contract: str | None = None,
):
    policy = EventLedgerV12EngineeringPolicy(checkpoint, market_checkpoint, contract)
    return lambda observation, configuration=None: policy(observation, configuration)
