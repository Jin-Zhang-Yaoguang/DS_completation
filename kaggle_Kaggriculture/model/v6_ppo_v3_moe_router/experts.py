"""Pure-Python contracts for PPO v3's verified-expert router.

The router chooses *one* production expert and at most one compatible market
expert.  Experts do not blend actions: a production expert owns the complete
atomic action plan for a turn, while a market expert may make an auditable,
bounded edit to that plan.  This module deliberately has no NumPy/JAX or
Kaggle-environments dependency so the same code can be packaged in a Kaggle
submission.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Protocol, Sequence, Set, Tuple
import copy


Obs = Mapping[str, Any]
Action = Dict[str, Any]
ActionFactory = Callable[[Obs], Mapping[str, Any]]
Predicate = Callable[[Obs], bool]

# These two mutable lists are the intentionally small, stable catalog surface
# used by ``main.py`` and data collectors.  Registration mutates them in place
# so ``from experts import PRODUCTION_EXPERTS`` remains current.
PRODUCTION_EXPERTS = []
MARKET_EXPERTS = []


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def copy_action(action: Optional[Mapping[str, Any]]) -> Action:
    """Return a submission-shaped deep copy without deciding legality.

    The compiler is responsible for final validation.  Keeping this helper
    permissive is important because valid Kaggriculture unit orders have
    different arities (MOVE, PICKUP, PLACE, PLANT, ...).
    """
    raw = action or {}
    return {
        "farmer": list(_get(raw, "farmer", None) or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in (_get(raw, "hands", None) or [])],
        "market": [list(order or []) for order in (_get(raw, "market", None) or [])],
    }


@dataclass(frozen=True)
class ActionFootprint:
    """Observable action difference, used to reject no-op interventions.

    It intentionally records the action closure rather than any unobservable
    expert internals.  Counterfactual data may use ``effective`` as a hard
    eligibility flag: an expert that did not alter a deployable action cannot
    be labelled as a positive intervention.
    """

    changed_farmer: bool = False
    changed_hands: Tuple[int, ...] = ()
    added_market: Tuple[Tuple[Any, ...], ...] = ()
    removed_market: Tuple[Tuple[Any, ...], ...] = ()
    changed_market_slots: Tuple[int, ...] = ()
    notes: Tuple[str, ...] = ()

    @property
    def effective(self) -> bool:
        return bool(
            self.changed_farmer
            or self.changed_hands
            or self.added_market
            or self.removed_market
            or self.changed_market_slots
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "changed_farmer": self.changed_farmer,
            "changed_hands": list(self.changed_hands),
            "added_market": [list(x) for x in self.added_market],
            "removed_market": [list(x) for x in self.removed_market],
            "changed_market_slots": list(self.changed_market_slots),
            "notes": list(self.notes),
            "effective": self.effective,
        }


def action_footprint(before: Optional[Mapping[str, Any]], after: Optional[Mapping[str, Any]]) -> ActionFootprint:
    """Compute a deterministic, serialisable action-level footprint."""
    left, right = copy_action(before), copy_action(after)
    changed_hands = tuple(
        index
        for index in range(max(len(left["hands"]), len(right["hands"])))
        if (left["hands"][index] if index < len(left["hands"]) else ["PASS"])
        != (right["hands"][index] if index < len(right["hands"]) else ["PASS"])
    )
    left_market = [tuple(order) for order in left["market"]]
    right_market = [tuple(order) for order in right["market"]]
    changed_slots = tuple(
        index
        for index in range(min(len(left_market), len(right_market)))
        if left_market[index] != right_market[index]
    )
    return ActionFootprint(
        changed_farmer=left["farmer"] != right["farmer"],
        changed_hands=changed_hands,
        added_market=tuple(right_market[len(left_market):]),
        removed_market=tuple(left_market[len(right_market):]),
        changed_market_slots=changed_slots,
    )


@dataclass(frozen=True)
class ActionPlan:
    """A complete atomic plan emitted by a production expert.

    ``action`` must already contain farmer/hands/market fields.  ``tags`` are
    semantic, not learned values: they make compatibility explicit and become
    part of the counterfactual manifest.
    """

    action: Mapping[str, Any]
    tags: Tuple[str, ...] = ()
    template_id: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProductionProposal:
    expert_id: str
    plan: Optional[ActionPlan]
    eligible: bool
    reason: str = ""
    preconditions: Tuple[str, ...] = ()

    @property
    def action(self) -> Optional[Mapping[str, Any]]:
        return None if self.plan is None else self.plan.action


@dataclass(frozen=True)
class MarketProposal:
    expert_id: str
    eligible: bool
    reason: str = ""
    preconditions: Tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def apply(self, action: Mapping[str, Any], obs: Obs) -> Action:
        """Override in concrete experts; default is deliberately a no-op."""
        return copy_action(action)


@dataclass(frozen=True)
class ExpertDecision:
    """Router output before action compilation.

    IDs rather than object references make the decision serialisable into D2/D3
    records and prevent a training process from silently selecting an expert
    not present in the submission catalog.
    """

    production_id: str
    market_id: Optional[str] = None
    score: Optional[float] = None
    uncertainty: Optional[float] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ProductionExpert(Protocol):
    """A production expert is a flat candidate, not a V1 residual."""

    expert_id: str
    tags: Tuple[str, ...]

    def propose(self, obs: Obs) -> ProductionProposal:
        ...


class MarketExpert(Protocol):
    """A bounded market residual compatible with selected production plans."""

    expert_id: str
    compatible_production_ids: Tuple[str, ...]
    required_production_tags: Tuple[str, ...]

    def propose(self, obs: Obs, production: ProductionProposal) -> MarketProposal:
        ...

    def is_compatible(self, obs: Obs, production: ProductionProposal) -> bool:
        ...


class _BaseExpert:
    def __init__(
        self,
        expert_id: str,
        *,
        tags: Iterable[str] = (),
        predicate: Optional[Predicate] = None,
        description: str = "",
    ) -> None:
        if not expert_id:
            raise ValueError("expert_id must be non-empty")
        self.expert_id = str(expert_id)
        self.tags = tuple(sorted({str(tag) for tag in tags if str(tag)}))
        self._predicate = predicate
        self.description = str(description)

    def _eligible(self, obs: Obs) -> Tuple[bool, str]:
        if self._predicate is None:
            return True, ""
        try:
            return (True, "") if bool(self._predicate(obs)) else (False, "precondition_false")
        except Exception as exc:  # experts must fail closed for submissions
            return False, "precondition_error:%s" % type(exc).__name__


class V1ProductionExpert(_BaseExpert):
    """Adapter for V1 as a peer production expert, baseline and fallback.

    The caller injects the V1 callable.  This avoids importing a development
    package in a Kaggle archive and makes V1 no more privileged than any other
    candidate in the router's selection layer.
    """

    def __init__(self, action_factory: ActionFactory, expert_id: str = "E_V1") -> None:
        super().__init__(expert_id, tags=("v1", "full_plan", "fallback"), description="V1 peer expert")
        self._action_factory = action_factory

    def propose(self, obs: Obs) -> ProductionProposal:
        try:
            return ProductionProposal(
                expert_id=self.expert_id,
                plan=ActionPlan(action=copy_action(self._action_factory(obs)), tags=self.tags, template_id=self.expert_id),
                eligible=True,
            )
        except Exception as exc:
            return ProductionProposal(self.expert_id, None, False, "action_factory_error:%s" % type(exc).__name__)


class RouteTemplateProductionExpert(_BaseExpert):
    """Adapter for a complete route/template callable.

    A callable passed here must be independently executable for the current
    state.  A partial template that secretly relies on V1 state must instead be
    represented as a market residual, not registered as a flat expert.
    """

    def __init__(
        self,
        expert_id: str,
        action_factory: ActionFactory,
        *,
        template_id: Optional[str] = None,
        tags: Iterable[str] = ("full_plan",),
        predicate: Optional[Predicate] = None,
        allowed_steps: Optional[Tuple[int, int]] = None,
        description: str = "",
    ) -> None:
        super().__init__(expert_id, tags=tags, predicate=predicate, description=description)
        self._action_factory = action_factory
        self.template_id = template_id or expert_id
        self.allowed_steps = allowed_steps

    def propose(self, obs: Obs) -> ProductionProposal:
        eligible, reason = self._eligible(obs)
        step = int(_get(obs, "step", 0) or 0)
        if eligible and self.allowed_steps is not None:
            start, stop = self.allowed_steps
            if not int(start) <= step <= int(stop):
                eligible, reason = False, "outside_step_window"
        if not eligible:
            return ProductionProposal(self.expert_id, None, False, reason)
        try:
            return ProductionProposal(
                expert_id=self.expert_id,
                plan=ActionPlan(
                    action=copy_action(self._action_factory(obs)),
                    tags=self.tags,
                    template_id=self.template_id,
                    metadata={"description": self.description},
                ),
                eligible=True,
            )
        except Exception as exc:
            return ProductionProposal(self.expert_id, None, False, "action_factory_error:%s" % type(exc).__name__)


class CallableMarketExpert(_BaseExpert):
    """Reusable bounded market-expert adapter.

    ``transform`` receives a copied submission action and must return an
    action-shaped mapping.  Compatibility is declared instead of inferred so
    data collection can audit why a candidate was masked.
    """

    def __init__(
        self,
        expert_id: str,
        transform: Callable[[Action, Obs], Mapping[str, Any]],
        *,
        compatible_production_ids: Iterable[str] = (),
        required_production_tags: Iterable[str] = (),
        predicate: Optional[Predicate] = None,
        description: str = "",
    ) -> None:
        super().__init__(expert_id, tags=("market_residual",), predicate=predicate, description=description)
        self._transform = transform
        self.compatible_production_ids = tuple(sorted({str(x) for x in compatible_production_ids if str(x)}))
        self.required_production_tags = tuple(sorted({str(x) for x in required_production_tags if str(x)}))

    def is_compatible(self, obs: Obs, production: ProductionProposal) -> bool:
        if not production.eligible or production.plan is None:
            return False
        if self.compatible_production_ids and production.expert_id not in self.compatible_production_ids:
            return False
        plan_tags = set(production.plan.tags)
        return set(self.required_production_tags).issubset(plan_tags)

    def propose(self, obs: Obs, production: ProductionProposal) -> MarketProposal:
        eligible, reason = self._eligible(obs)
        if eligible and not self.is_compatible(obs, production):
            eligible, reason = False, "incompatible_production"
        return MarketProposal(
            expert_id=self.expert_id,
            eligible=eligible,
            reason=reason,
            metadata={"description": self.description},
        )

    def apply(self, action: Mapping[str, Any], obs: Obs) -> Action:
        try:
            return copy_action(self._transform(copy_action(action), obs))
        except Exception:
            # The compiler will also protect closure.  A market expert must
            # never turn an exception into a submission failure.
            return copy_action(action)


_PRODUCTION_BY_ID: Dict[str, ProductionExpert] = {}
_MARKET_BY_ID: Dict[str, MarketExpert] = {}


def register_production_expert(expert: ProductionExpert, *, replace: bool = False) -> None:
    """Register a flat production expert for local collection/submission.

    Registration is explicit.  The module never imports a development V1
    package implicitly, which keeps a clean Kaggle archive deterministic.
    """
    expert_id = str(getattr(expert, "expert_id", ""))
    if not expert_id:
        raise ValueError("production expert has no expert_id")
    if expert_id in _PRODUCTION_BY_ID and not replace:
        raise ValueError("duplicate production expert: %s" % expert_id)
    _PRODUCTION_BY_ID[expert_id] = expert
    if expert_id not in PRODUCTION_EXPERTS:
        PRODUCTION_EXPERTS.append(expert_id)


def register_market_expert(expert: MarketExpert, *, replace: bool = False) -> None:
    """Register a bounded market expert for local collection/submission."""
    expert_id = str(getattr(expert, "expert_id", ""))
    if not expert_id:
        raise ValueError("market expert has no expert_id")
    if expert_id in _MARKET_BY_ID and not replace:
        raise ValueError("duplicate market expert: %s" % expert_id)
    _MARKET_BY_ID[expert_id] = expert
    if expert_id not in MARKET_EXPERTS:
        MARKET_EXPERTS.append(expert_id)


def get_production_expert(expert_id: str) -> ProductionExpert:
    try:
        return _PRODUCTION_BY_ID[str(expert_id)]
    except KeyError:
        raise KeyError("unregistered production expert: %s" % expert_id)


def get_market_expert(expert_id: str) -> MarketExpert:
    try:
        return _MARKET_BY_ID[str(expert_id)]
    except KeyError:
        raise KeyError("unregistered market expert: %s" % expert_id)


def build_base_action(obs: Obs, production_id: str) -> Action:
    """Build an independently executable action from one production expert.

    A caller should pass the returned action to ``ActionCompiler`` alongside
    its separately generated V1 fallback.  This function deliberately raises
    on an unknown/ineligible ID: silently substituting V1 here would recreate
    the V1-default privilege that PPO v3 removes.
    """
    expert = get_production_expert(production_id)
    proposal = expert.propose(obs)
    if not proposal.eligible or proposal.plan is None:
        raise ValueError("ineligible production expert %s: %s" % (production_id, proposal.reason))
    return copy_action(proposal.plan.action)


def apply_market_expert(obs: Obs, action: Mapping[str, Any], market_id: Optional[str]) -> Action:
    """Apply one registered market residual by ID, with no-op None support.

    Compatibility is enforced by ``MarketExpert.propose`` when a selected
    production proposal is available.  This compact helper is for callers
    which have already performed that mask calculation and only need an
    action-level replay.
    """
    if market_id in (None, "", "M_NONE", "none"):
        return copy_action(action)
    expert = get_market_expert(str(market_id))
    try:
        return copy_action(expert.apply(copy_action(action), obs))
    except Exception:
        return copy_action(action)


def propose_market_expert(obs: Obs, production: ProductionProposal, market_id: Optional[str]) -> Optional[MarketProposal]:
    """Return a compatibility-checked market proposal for the selected plan."""
    if market_id in (None, "", "M_NONE", "none"):
        return None
    expert = get_market_expert(str(market_id))
    return expert.propose(obs, production)


def apply_market_proposal(
    market_expert: Optional[MarketExpert],
    market_proposal: Optional[MarketProposal],
    action: Mapping[str, Any],
    obs: Obs,
) -> Action:
    """Apply only an eligible proposal; otherwise return an exact action copy."""
    if market_expert is None or market_proposal is None or not market_proposal.eligible:
        return copy_action(action)
    try:
        return copy_action(market_expert.apply(action, obs))
    except Exception:
        return copy_action(action)


def eligible_production(experts: Sequence[ProductionExpert], obs: Obs) -> Tuple[ProductionProposal, ...]:
    """Collect proposals fail-closed while preserving the supplied flat order."""
    proposals = []
    for expert in experts:
        try:
            proposals.append(expert.propose(obs))
        except Exception as exc:
            proposals.append(ProductionProposal(getattr(expert, "expert_id", "unknown"), None, False, "propose_error:%s" % type(exc).__name__))
    return tuple(proposals)
