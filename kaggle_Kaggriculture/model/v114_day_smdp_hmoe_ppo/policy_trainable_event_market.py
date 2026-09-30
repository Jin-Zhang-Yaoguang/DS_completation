"""On-policy event-boundary transaction policy for V12."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np

from build_event_market_dataset import PROCUREMENT_HEADS, QUANTITY_TIERS, TRANSACTION_HEADS
from event_ledger import EventKind, MarketEvent, TransactionIntent
from event_ledger_controller import economy_snapshot
from event_market_ppo_math import calibrated_presence_logits, factorized_logp_entropy
from policy_event_market_hmoe import EVENT_INDEX, LearnedEventMarketPolicy
import features


class TrainableEventMarketPolicy(LearnedEventMarketPolicy):
    qualification_status = "ON_POLICY_EVENT_MARKET_NOT_G2_NOT_GOLD"

    def __init__(self, checkpoint: Path, *, rollout_seed: int, deterministic: bool = False):
        super().__init__(checkpoint)
        self.rng = np.random.default_rng(int(rollout_seed))
        self.deterministic = bool(deterministic)
        self.transitions: list[dict[str, Any]] = []
        self.pending: dict[str, Any] | None = None

    @staticmethod
    def _money(observation: Mapping[str, Any]) -> float:
        return float(economy_snapshot(observation).money)

    def _close(self, observation: Mapping[str, Any], *, terminal: bool) -> None:
        if self.pending is None:
            return
        end_step = int(observation.get("step", 719) or 719)
        self.pending.update({
            "end_step": end_step,
            "duration_turns": max(1, end_step - int(self.pending["start_step"])),
            "reward": (self._money(observation) - float(self.pending["money_start"])) / 1000.0,
            "terminal": bool(terminal),
        })
        self.transitions.append(self.pending)
        self.pending = None

    def __call__(self, observation: Mapping[str, Any], event: MarketEvent) -> list[TransactionIntent]:
        state = economy_snapshot(observation)
        self._close(observation, terminal=event.kind == EventKind.TERMINAL_WINDOW)
        if event.kind == EventKind.TERMINAL_WINDOW or state.step >= 671:
            return super().__call__(observation, MarketEvent(
                event.event_id, event.generation, EventKind.TERMINAL_WINDOW,
                event.opened_step, True,
            ))
        encoded = features.encode_observation(observation)
        event_type = EVENT_INDEX[event.kind]
        output = self._apply(
            self.params,
            jnp.asarray(encoded["global"][:60])[None],
            jnp.asarray(encoded["board"])[None],
            jnp.asarray([event_type], jnp.int32),
        )
        raw_presence = np.asarray(output["presence_logits"][0], np.float32)
        raw_quantity = np.asarray(output["quantity_logits"][0], np.float32)
        presence_mask = np.zeros(len(TRANSACTION_HEADS), np.bool_)
        if event_type == 0:
            presence_mask[:len(PROCUREMENT_HEADS)] = self.thresholds[:len(PROCUREMENT_HEADS)] <= 1.0
        else:
            for index, head in enumerate(TRANSACTION_HEADS[len(PROCUREMENT_HEADS):], start=len(PROCUREMENT_HEADS)):
                _, _, product = head.partition(":")
                presence_mask[index] = int(state.inventory.get(product, 0) or 0) > 0
        adjusted = np.asarray(calibrated_presence_logits(
            jnp.asarray(raw_presence[None]), jnp.asarray(self.thresholds[None]),
            jnp.asarray(presence_mask[None]),
        )[0])
        probability = 1.0 / (1.0 + np.exp(-np.clip(adjusted, -30, 30)))
        if self.deterministic:
            presence_action = (adjusted >= 0).astype(np.int8)
        else:
            presence_action = (self.rng.random(len(probability)) < probability).astype(np.int8)
        presence_action[~presence_mask] = 0
        quantity_mask = np.zeros((len(TRANSACTION_HEADS), len(QUANTITY_TIERS)), np.bool_)
        quantity_mask[:, 1:] = True
        quantity_action = np.zeros(len(TRANSACTION_HEADS), np.int8)
        for index in np.flatnonzero(presence_action):
            logits = raw_quantity[index].copy() / 0.5
            logits[~quantity_mask[index]] = -np.inf
            if self.deterministic:
                quantity_action[index] = int(np.argmax(logits))
            else:
                stable = logits - np.max(logits[quantity_mask[index]])
                p = np.where(quantity_mask[index], np.exp(stable), 0.0)
                p /= p.sum()
                quantity_action[index] = int(self.rng.choice(len(p), p=p))
        old_logp, entropy = factorized_logp_entropy(
            jnp.asarray(adjusted[None]), jnp.asarray(raw_quantity[None] / 0.5),
            jnp.asarray(presence_action[None]), jnp.asarray(quantity_action[None]),
            jnp.asarray(presence_mask[None]), jnp.asarray(quantity_mask[None]),
        )
        value = float(np.asarray(output["value"][0]))
        self.pending = {
            "global": np.asarray(encoded["global"][:60], np.float16),
            "board": np.asarray(encoded["board"], np.float16),
            "event_type": int(event_type),
            "presence_action": presence_action,
            "quantity_action": quantity_action,
            "presence_mask": presence_mask,
            "quantity_mask": quantity_mask,
            "old_logp": float(np.asarray(old_logp[0])),
            "old_entropy": float(np.asarray(entropy[0])),
            "value": value,
            "start_step": state.step,
            "money_start": float(state.money),
        }
        # Convert sampled action through the same bounded ledger intent contract.
        original_thresholds = self.thresholds
        try:
            self.thresholds = np.where(presence_action > 0, 0.0, 2.0).astype(np.float32)
            # Quantity is not overridden by the parent; build intents directly below.
            intents = []
            day = state.step // 24
            cash_floor = max(500, int(0.20 * state.money)) if day < 27 else 0
            for index in np.flatnonzero(presence_action):
                head = TRANSACTION_HEADS[int(index)]
                operation, _, product = head.partition(":")
                product = product or None
                quantity = int(QUANTITY_TIERS[int(quantity_action[index])])
                if operation in {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"}:
                    unit_price, max_spend = self._price(observation, operation, product, quantity)
                    target_total = None
                    if operation == "HIRE": target_total = min(16, state.workers + quantity)
                    elif operation == "BUY_LAND": target_total = min(4, state.unlocked_land + quantity)
                    elif operation == "BUY_SEED" and product: target_total = min(100, int(state.seeds.get(product, 0)) + quantity)
                    elif operation == "BUY_PRODUCT" and product: target_total = min(100, int(state.inventory.get(product, 0)) + quantity)
                    intents.append(TransactionIntent(
                        operation, product, quantity, unit_price, max_spend, cash_floor,
                        min(event.opened_step + 1, 670), target_total=target_total,
                        worker_cap=16, land_cap=4, animal_cap=16,
                    ))
                elif operation == "SELL" and product:
                    available = int(state.inventory.get(product, 0))
                    if available > 0:
                        intents.append(TransactionIntent(
                            operation, product, min(quantity, available), 0, 0, 0,
                            event.opened_step, retain_total=max(0, available - quantity),
                        ))
            return intents[:10]
        finally:
            self.thresholds = original_thresholds

    def finalize_episode(self, observation: Mapping[str, Any]) -> list[dict[str, Any]]:
        self._close(observation, terminal=True)
        return self.transitions
