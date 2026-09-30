"""Q0 日级 Router：资格、驻留、滞回、切换成本和终止申请。"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any

from contracts import DailyContract, realize_contract, transition_violations
from experts import BalancedExpert, BalancedGenome, build_expert_registry
from schema import CanonicalState
from state_ledger import RuntimeFeedback


@dataclass
class RouterSeatState:
    active_expert_id: str | None = None
    active_contract: DailyContract | None = None
    active_since_day: int = 0
    last_evaluation_day: int = -1
    switch_count: int = 0
    termination_requests: int = 0
    last_scores: dict[str, float] = field(default_factory=dict)
    trace: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=120))


class DailyRouter:
    """正常只在日初选择；重大事件先形成可审计终止申请。"""

    def __init__(self, allow_unqualified_for_tests: bool = False,
                 balanced_genome: BalancedGenome | dict[str, Any] | None = None) -> None:
        self.experts = build_expert_registry(balanced_genome)
        self.allow_unqualified_for_tests = bool(allow_unqualified_for_tests)
        self.by_seat = {0: RouterSeatState(), 1: RouterSeatState()}
        self.audit: Counter[str] = Counter()
        self.entry_hysteresis = 0.12
        self.exit_hysteresis = 0.05

    @property
    def qualified_experts(self) -> tuple[str, ...]:
        return tuple(
            expert_id for expert_id, expert in self.experts.items()
            if expert.qualification.router_enabled
        )

    @property
    def implemented_experts(self) -> tuple[str, ...]:
        return tuple(self.experts)

    def reset_seat(self, seat: int) -> None:
        self.by_seat[seat] = RouterSeatState()

    def current_contract(self, seat: int) -> DailyContract | None:
        return self.by_seat[seat].active_contract

    @staticmethod
    def _hard_termination(contract: DailyContract, state: CanonicalState,
                          feedback: RuntimeFeedback) -> bool:
        rules = dict(contract.terminate_if)
        if "cash_below" in rules and state.money < int(rules["cash_below"]):
            return True
        if "feed_risk_above" in rules and feedback.feed_risk > float(rules["feed_risk_above"]):
            return True
        if "day_after" in rules and state.day > int(rules["day_after"]):
            return True
        if rules.get("yarn_absent") and contract.expert_id == "YARN_WOOL" and "YARN_STORE" not in state.shops:
            return True
        return False

    def _routable(self, expert_id: str) -> bool:
        expert = self.experts[expert_id]
        return bool(expert.qualification.router_enabled or self.allow_unqualified_for_tests)

    def _score(self, expert_id: str, state: CanonicalState, feedback: RuntimeFeedback,
               current: DailyContract | None) -> float:
        expert = self.experts[expert_id]
        eligibility = expert.eligibility(state, feedback, current)
        if not self._routable(expert_id) or not bool(eligibility.get("eligible", False)):
            return float("-inf")
        confidence = float(eligibility.get("confidence", 0.0))
        score = 0.45 + confidence
        if expert_id == BalancedExpert.expert_id:
            score = 0.65
        score -= 0.20 * min(1.0, feedback.cash_risk)
        score -= 0.15 * min(1.0, feedback.labor_pressure)
        score -= 0.10 * min(1.0, feedback.feed_risk)
        if current is not None and current.expert_id == expert_id:
            score += self.exit_hysteresis
        return score

    def _choose(self, state: CanonicalState, feedback: RuntimeFeedback,
                runtime: RouterSeatState, hard_termination: bool) -> tuple[str, dict[str, float]]:
        scores = {expert_id: self._score(expert_id, state, feedback, runtime.active_contract)
                  for expert_id in self.experts}
        fallback = BalancedExpert.expert_id
        best = max(scores, key=lambda key: (scores[key], key == fallback, key))
        current = runtime.active_expert_id
        if current is not None and not hard_termination and scores.get(current, float("-inf")) > float("-inf"):
            age = state.day - runtime.active_since_day
            if age < int(runtime.active_contract.min_dwell_days if runtime.active_contract else 1):
                best = current
                self.audit["dwell_hold"] += 1
            elif best != current and scores[best] < scores[current] + self.entry_hysteresis:
                best = current
                self.audit["hysteresis_hold"] += 1
        if scores.get(best, float("-inf")) == float("-inf"):
            best = fallback
        return best, scores

    def select(self, state: CanonicalState, feedback: RuntimeFeedback) -> tuple[DailyContract, bool]:
        runtime = self.by_seat[state.seat]
        current = runtime.active_contract
        hard = bool(current and self._hard_termination(current, state, feedback))
        major_event = bool(state.new_shops or feedback.cash_risk >= 0.9 or feedback.feed_risk >= 0.9 or feedback.terminal)
        day_boundary = state.hour == 0 and runtime.last_evaluation_day != state.day
        # Balanced 是硬风险回退，不能对自身反复发起“提前终止”。
        early_request = bool(current and current.expert_id != BalancedExpert.expert_id and hard and major_event)
        if early_request:
            runtime.termination_requests += 1
            self.audit["termination_request"] += 1
        if current is not None and not day_boundary and not early_request:
            self.audit["cached_contract"] += 1
            realized = realize_contract(current, state, feedback.blocked_reasons)
            runtime.active_contract = realized
            return realized, False

        chosen, scores = self._choose(state, feedback, runtime, hard)
        expert = self.experts[chosen]
        candidate = expert.propose(state, feedback, current)
        violations = transition_violations(
            current, candidate, state.day, state.money,
            active_since_day=runtime.active_since_day if current is not None else None,
            hard_termination=hard,
        )
        if violations and chosen != BalancedExpert.expert_id:
            self.audit["candidate_rejected"] += 1
            chosen = BalancedExpert.expert_id
            expert = self.experts[chosen]
            candidate = expert.propose(state, feedback, current)
            violations = transition_violations(
                current, candidate, state.day, state.money,
                active_since_day=runtime.active_since_day if current is not None else None,
                hard_termination=hard,
            )
        if violations:
            # Balanced 仍不可签发时，保持上一个合法合同；首步则显式失败。
            self.audit["contract_guard_reject"] += 1
            if current is None:
                raise RuntimeError(f"no legal initial contract: {violations}")
            realized = realize_contract(current, state, feedback.blocked_reasons)
            runtime.active_contract = realized
            return realized, False
        switched = current is not None and current.expert_id != chosen
        if current is None or switched:
            runtime.active_since_day = state.day
        if switched:
            runtime.switch_count += 1
            self.audit["switch"] += 1
        runtime.active_expert_id = chosen
        runtime.active_contract = realize_contract(candidate, state, feedback.blocked_reasons)
        runtime.last_evaluation_day = state.day
        runtime.last_scores = scores
        runtime.trace.append({
            "step": state.step, "day": state.day, "expert_id": chosen, "switched": switched,
            "hard_termination": hard, "scores": dict(scores), "contract_id": candidate.contract_id,
        })
        self.audit["daily_evaluation"] += 1
        self.audit[f"selected_{chosen}"] += 1
        return runtime.active_contract, switched

    def status(self) -> dict[str, Any]:
        return {
            "implemented_experts": list(self.implemented_experts),
            "routable_experts": list(self.qualified_experts),
            "qualification": {
                key: expert.qualification.__dict__ for key, expert in self.experts.items()
            },
            "audit": dict(self.audit),
            "seats": {
                seat: {
                    "active_expert": runtime.active_expert_id,
                    "active_contract": runtime.active_contract.contract_id if runtime.active_contract else None,
                    "active_since_day": runtime.active_since_day,
                    "last_evaluation_day": runtime.last_evaluation_day,
                    "switch_count": runtime.switch_count,
                    "termination_requests": runtime.termination_requests,
                    "last_scores": dict(runtime.last_scores),
                    "trace": list(runtime.trace),
                }
                for seat, runtime in self.by_seat.items()
            },
        }
