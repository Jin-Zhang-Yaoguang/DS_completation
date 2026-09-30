"""Checkpoint-backed V12 event transaction-intent policy."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Mapping

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np

HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))
import action_space as space  # noqa: E402
import features  # noqa: E402

from build_event_market_dataset import (  # noqa: E402
    EVENT_TYPES, PROCUREMENT_HEADS, QUANTITY_TIERS, TRANSACTION_HEADS,
)
from event_ledger import EventKind, MarketEvent, TransactionIntent  # noqa: E402
from event_ledger_controller import economy_snapshot  # noqa: E402
from model_event_market_hmoe import EventMarketHMoE  # noqa: E402
from enterprise_contracts_v12 import resolve_contract  # noqa: E402


EVENT_INDEX = {
    EventKind.DAY_START: 0,
    EventKind.SHOP_UNLOCK: 0,
    EventKind.INVENTORY_THRESHOLD: 1,
    EventKind.CASH_CRISIS: 1,
    EventKind.OPTION_FAILURE: 1,
    EventKind.TERMINAL_WINDOW: 2,
    EventKind.EXPLICIT_RETRY_AFTER_REJECTION: 1,
}


def _fib(index: int) -> int:
    a, b = 1, 1
    for _ in range(max(0, index)):
        a, b = b, a + b
    return a


class LearnedEventMarketPolicy:
    qualification_status = "EVENT_MARKET_BC_WARMSTART_ONLY_NOT_G2_NOT_PPO_NOT_GOLD"

    def __init__(self, checkpoint: Path, contract: str | None = None):
        payload = serialization.msgpack_restore(Path(checkpoint).read_bytes())
        if payload.get("strategy_parent") is not None:
            raise ValueError("event market policy must remain an independent lineage")
        if payload.get("inherits_historical_checkpoint") is not False:
            raise ValueError("historical checkpoint inheritance is forbidden")
        if payload.get("historical_agent_online_action_source") is not False:
            raise ValueError("historical online action source is forbidden")
        if payload.get("architecture") != "hard-event-router-three-transaction-experts-v1":
            raise ValueError("unexpected event market architecture")
        self.params = payload["params"]
        self.thresholds = np.asarray(payload["presence_thresholds"], np.float32)
        self.model = EventMarketHMoE()
        self.contract = resolve_contract(contract)
        self._apply = jax.jit(
            lambda params, global_features, board, event_type: self.model.apply(
                {"params": params}, global_features, board, event_type
            )
        )
        self.calls = 0
        self.proposed = 0
        self.proposed_by_head: dict[str, int] = {}
        self.contract_blocks = 0

    @staticmethod
    def _price(observation: Mapping[str, Any], operation: str, product: str | None, quantity: int) -> tuple[int, int]:
        state = economy_snapshot(observation)
        if operation == "HIRE":
            current = int((observation.get("farms") or [])[int(observation.get("player", 0) or 0)].get("hires_today", 0) or 0)
            costs = [_fib(current + offset) for offset in range(quantity)]
            return max(costs or [1]), sum(costs)
        if operation == "BUY_LAND":
            prices = (1000, 2000, 4000)
            start = max(0, state.unlocked_land - 1)
            costs = [prices[min(len(prices) - 1, start + offset)] for offset in range(quantity)]
            return max(costs or [1000]), sum(costs)
        if operation == "BUY_SEED" and product is not None:
            unit = space.SEED_COST[product]
        elif operation == "BUY_ANIMAL" and product is not None:
            unit = space.ANIMAL_COST[product]
        elif operation == "BUY_PRODUCT" and product is not None:
            market = observation.get("market", {}) or {}
            unit = int((market.get("prices", {}) or {}).get(product, space.BASE_PRICES.get(product, 1)) or 1)
        else:
            unit = 0
        return unit, unit * quantity

    def __call__(
        self, observation: Mapping[str, Any], event: MarketEvent
    ) -> list[TransactionIntent]:
        self.calls += 1
        state = economy_snapshot(observation)
        if event.kind == EventKind.TERMINAL_WINDOW:
            return [
                TransactionIntent(
                    "SELL", product, 100, 0, 0, 0, state.step,
                    retain_total=0,
                )
                for product in space.PRODUCTS
                if int(state.inventory.get(product, 0) or 0) > 0
            ]
        encoded = features.encode_observation(observation)
        event_type = EVENT_INDEX[event.kind]
        output = self._apply(
            self.params,
            jnp.asarray(encoded["global"][:60])[None],
            jnp.asarray(encoded["board"])[None],
            jnp.asarray([event_type], jnp.int32),
        )
        probability = np.asarray(jax.nn.sigmoid(output["presence_logits"])[0])
        quantity_index = np.asarray(jnp.argmax(output["quantity_logits"][0], axis=-1))
        selected = [
            index for index in range(len(TRANSACTION_HEADS))
            if probability[index] >= self.thresholds[index]
        ]
        if self.contract is not None:
            allowed = []
            for index in selected:
                if self.contract.allows_transaction(TRANSACTION_HEADS[index]):
                    allowed.append(index)
                else:
                    self.contract_blocks += 1
            selected = allowed
        selected.sort(key=lambda index: float(probability[index]), reverse=True)
        intents: list[TransactionIntent] = []
        day = state.step // 24
        cash_floor = max(500, int(0.20 * state.money)) if day < 27 else 0
        for index in selected[:10]:
            head = TRANSACTION_HEADS[index]
            operation, _, product = head.partition(":")
            product = product or None
            quantity = int(QUANTITY_TIERS[int(quantity_index[index])])
            if quantity <= 0:
                continue
            if operation in {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"}:
                if event_type != 0 or head not in PROCUREMENT_HEADS:
                    continue
                unit_price, max_spend = self._price(
                    observation, operation, product, quantity
                )
                target_total = None
                if operation == "HIRE":
                    target_total = min(16, state.workers + quantity)
                elif operation == "BUY_LAND":
                    target_total = min(4, state.unlocked_land + quantity)
                elif operation == "BUY_SEED" and product is not None:
                    target_total = min(100, int(state.seeds.get(product, 0)) + quantity)
                elif operation == "BUY_PRODUCT" and product is not None:
                    target_total = min(100, int(state.inventory.get(product, 0)) + quantity)
                intents.append(TransactionIntent(
                    operation, product, quantity, unit_price, max_spend,
                    cash_floor, min(event.opened_step + 1, 670),
                    target_total=target_total,
                    worker_cap=16, land_cap=4, animal_cap=16,
                ))
            elif operation == "SELL" and product is not None:
                available = int(state.inventory.get(product, 0))
                if available <= 0:
                    continue
                intents.append(TransactionIntent(
                    operation, product, min(quantity, available), 0, 0, 0,
                    event.opened_step, retain_total=max(0, available - quantity),
                ))
            self.proposed += 1
            self.proposed_by_head[head] = self.proposed_by_head.get(head, 0) + 1
        return intents

    def audit(self) -> dict:
        return {
            "calls": self.calls,
            "proposed": self.proposed,
            "enterprise_contract": self.contract.name if self.contract else None,
            "contract_blocks": self.contract_blocks,
            "proposed_by_head": dict(sorted(self.proposed_by_head.items())),
            "qualification_status": self.qualification_status,
        }
