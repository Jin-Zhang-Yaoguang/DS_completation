#!/usr/bin/env python3
"""V117 R2.1：严格状态—合同—日级 option HMoE 运行入口。

三个经营专家都已实现；资格门仍 fail-closed。当前线上运行只允许 Balanced 工程回退，直到
Replay-derived Foundation、R3 uplift 与 R4 Oracle 证据允许开放 specialist。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from contracts import DailyContract  # noqa: E402
from diagnostics import LossAttributionLedger  # noqa: E402
from executor import CommonExecutor, ExecutorTuning  # noqa: E402
from experts import BalancedGenome  # noqa: E402
from market import MarketController  # noqa: E402
from router import DailyRouter  # noqa: E402
from safety import ControlMode, SafetyRecoveryTerminalController  # noqa: E402
from schema import ENGINE_VERSION, VERSION, integer  # noqa: E402
from state_ledger import StateLedger  # noqa: E402


@dataclass
class SeatRuntime:
    executor: CommonExecutor = field(default_factory=CommonExecutor)
    market: MarketController = field(default_factory=MarketController)
    safety: SafetyRecoveryTerminalController = field(default_factory=SafetyRecoveryTerminalController)
    loss_attribution: LossAttributionLedger = field(default_factory=LossAttributionLedger)
    calls: int = 0
    last_contract: DailyContract | None = None
    last_mode: str = ControlMode.NORMAL.value
    control_rewrites: int = 0


class V117Policy:
    """将架构图所有在线节点接成一个确定性闭环。"""

    def __init__(self, allow_unqualified_for_tests: bool = False,
                 balanced_genome: BalancedGenome | Mapping[str, Any] | None = None,
                 executor_tuning: ExecutorTuning | Mapping[str, Any] | None = None) -> None:
        self.ledger = StateLedger()
        self.executor_tuning = (
            executor_tuning if isinstance(executor_tuning, ExecutorTuning)
            else ExecutorTuning.from_mapping(executor_tuning)
        )
        self.router = DailyRouter(
            allow_unqualified_for_tests=allow_unqualified_for_tests,
            balanced_genome=balanced_genome,
        )
        self.seats = {
            0: SeatRuntime(
                executor=CommonExecutor(self.executor_tuning),
                safety=SafetyRecoveryTerminalController(
                    self.executor_tuning.terminal_return_buffer,
                    self.executor_tuning.terminal_hire_cap,
                ),
            ),
            1: SeatRuntime(
                executor=CommonExecutor(self.executor_tuning),
                safety=SafetyRecoveryTerminalController(
                    self.executor_tuning.terminal_return_buffer,
                    self.executor_tuning.terminal_hire_cap,
                ),
            ),
        }

    def act(self, observation: Mapping[str, Any], configuration: Any = None) -> dict[str, Any]:
        seat = 1 if integer(observation.get("player")) == 1 else 0
        step = integer(observation.get("step"), integer(observation.get("day")) * 24 + integer(observation.get("hour")))
        if step == 0:
            self.seats[seat] = SeatRuntime(
                executor=CommonExecutor(self.executor_tuning),
                safety=SafetyRecoveryTerminalController(
                    self.executor_tuning.terminal_return_buffer,
                    self.executor_tuning.terminal_hire_cap,
                ),
            )
            self.router.reset_seat(seat)
        runtime = self.seats[seat]

        state, feedback = self.ledger.observe(observation)
        runtime.loss_attribution.observe(state)
        contract, switched = self.router.select(state, feedback)
        self.ledger.activate_contract(seat, contract, switched)
        execution = runtime.executor.act(state, contract, feedback)
        mode = runtime.safety.mode(state, feedback)
        market = runtime.market.act(
            state, contract, feedback, execution.unit_actions, execution.pending_plants,
            force_recovery=mode in {ControlMode.CASH_RECOVERY, ControlMode.SHED_RECOVERY},
            terminal=mode == ControlMode.TERMINAL,
        )
        controlled = runtime.safety.apply(state, contract, feedback, execution, market)
        runtime.loss_attribution.record_decision(
            state, contract, feedback, execution, market, controlled,
        )

        units = [controlled.action["farmer"], *controlled.action["hands"]]
        self.ledger.record_execution(
            seat, units, controlled.action["market"], execution.actor_tasks,
            execution.actor_roles, execution.overdue_tasks,
        )
        runtime.last_contract = contract
        runtime.last_mode = controlled.mode.value
        runtime.control_rewrites += controlled.rewrites
        runtime.calls += 1
        return dict(controlled.action)

    def status(self) -> dict[str, Any]:
        return {
            "version": VERSION,
            "engine": ENGINE_VERSION,
            "architecture": "STATE_CONTRACT_DAILY_OPTION_HMOE",
            "executor_tuning": self.executor_tuning.stable_payload(),
            "router": self.router.status(),
            "seats": {
                seat: {
                    "calls": runtime.calls,
                    "contract": runtime.last_contract.contract_id if runtime.last_contract else None,
                    "expert": runtime.last_contract.expert_id if runtime.last_contract else None,
                    "control_mode": runtime.last_mode,
                    "control_rewrites": runtime.control_rewrites,
                    "executor": dict(runtime.executor.audit),
                    "market": dict(runtime.market.audit),
                    "safety": dict(runtime.safety.audit),
                    "loss_attribution": runtime.loss_attribution.status(),
                    "ledger": self.ledger.status(seat),
                }
                for seat, runtime in self.seats.items()
            },
        }


_POLICY = V117Policy()


def agent(observation: Mapping[str, Any], configuration: Any = None) -> dict[str, Any]:
    return _POLICY.act(observation, configuration)


def model_status() -> dict[str, Any]:
    return _POLICY.status()
