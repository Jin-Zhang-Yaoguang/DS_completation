"""Isolated registry for V1/V2/V5/V8 and eight pre-registered variants.

Every call to :func:`create_agent` loads fresh module objects.  In particular,
V5's bare imports (``base_agent``, ``v1_fallback`` and ``routes``) are rebound
only while its module is executed and are restored immediately afterwards.
This avoids cross-expert state leakage during pairwise evaluation.
"""

from __future__ import annotations

import importlib.util
import inspect
import itertools
import sys
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Mapping

try:
    from .variants import apply_transforms
except ImportError:  # direct-file compatibility for local evaluation scripts
    from variants import apply_transforms


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
_LOAD_LOCK = threading.RLock()
_MODULE_SEQUENCE = itertools.count()
_MISSING = object()


@dataclass(frozen=True)
class ExpertSpec:
    """Auditable registration record for one complete callable agent."""

    model_id: str
    parent: str | None
    lineage: tuple[str, ...]
    family: str
    change_scope: str
    mechanism: str
    expected_effect: str
    tag: str
    source: str
    transforms: tuple[str, ...] = ()
    module_overrides: tuple[tuple[str, Any], ...] = ()
    is_variant: bool = False

    @property
    def expert_id(self) -> str:
        """Compatibility alias for older evaluator code."""
        return self.model_id

    def factory(self) -> "RegisteredAgent":
        """Create a fresh state-isolated instance of this registered model."""
        return create_agent(self)

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


def _baseline(
    expert_id: str,
    family: str,
    mechanism: str,
    source: str,
) -> ExpertSpec:
    return ExpertSpec(
        model_id=expert_id,
        parent=None,
        lineage=(expert_id,),
        family=family,
        change_scope="完整生产路线",
        mechanism=mechanism,
        expected_effect="作为完整固定专家和配对评测控制组，不声称新增收益。",
        tag="保留基线",
        source=source,
    )


def _variant(
    expert_id: str,
    parent: str,
    family: str,
    mechanism: str,
    expected_effect: str,
    *,
    transforms: tuple[str, ...] = (),
    module_overrides: tuple[tuple[str, Any], ...] = (),
) -> ExpertSpec:
    return ExpertSpec(
        model_id=expert_id,
        parent=parent,
        lineage=BASELINE_SPECS[parent].lineage + (expert_id,),
        family=family,
        change_scope="仅市场wrapper",
        mechanism=mechanism,
        expected_effect=expected_effect,
        tag="待评测",
        source=BASELINE_SPECS[parent].source,
        transforms=transforms,
        module_overrides=module_overrides,
        is_variant=True,
    )


BASELINE_SPECS: dict[str, ExpertSpec] = {
    "baseline_v1": _baseline(
        "baseline_v1",
        "v1_adaptive_market",
        "V1 双路线选择、市场排序、安全修复和终局清仓的原始完整执行路径。",
        "v1_adaptive_market/main.py",
    ),
    "baseline_v2": _baseline(
        "baseline_v2",
        "v2_survival_guard",
        "V1 路线族加通用种子余量/生存保护的完整执行路径。",
        "v2_survival_guard/main.py",
    ),
    "baseline_v5": _baseline(
        "baseline_v5",
        "v5_rule_hybrid",
        "冠军片段、YARN 条件路线和陌生结构回退 V1 的四层完整执行路径。",
        "v5_rule_hybrid/main.py",
    ),
    "baseline_v8": _baseline(
        "baseline_v8",
        "v8_kawa_lead2_slot",
        "Kawashigi 五路线条件选择、两回合 premium preempt 和 slot 排序的完整执行路径。",
        "v8_kawa_lead2_slot/main.py",
    ),
}


# Exactly eight hypotheses.  These are residual/ablation variants of the four
# registered complete agents; none is represented as a new production route.
VARIANT_SPECS: dict[str, ExpertSpec] = {
    "v1_topdays": _variant(
        "v1_topdays",
        "baseline_v1",
        "v1_adaptive_market+topdays",
        "只在第 10/17/24 天把已有 EGG/MILK/WOOL SELL 数量减半。",
        "减少已审计中期节点的动物品集中抛售，争取更好的后续成交价。",
        transforms=("animal_half_topdays",),
    ),
    "v2_topdays": _variant(
        "v2_topdays",
        "baseline_v2",
        "v2_survival_guard+topdays",
        "在 V2 完整安全执行器之后，仅于第 10/17/24 天减半动物品 SELL。",
        "检验相同市场残差能否与 V2 的生存保护产生可迁移增益。",
        transforms=("animal_half_topdays",),
    ),
    "v5_topdays": _variant(
        "v5_topdays",
        "baseline_v5",
        "v5_rule_hybrid+topdays",
        "保持 V5 四层生产路线，只在第 10/17/24 天减半动物品 SELL。",
        "把路线收益和有限时点市场节流解耦，降低季中价格冲击。",
        transforms=("animal_half_topdays",),
    ),
    "v8_topdays": _variant(
        "v8_topdays",
        "baseline_v8",
        "v8_kawa+topdays",
        "保持 V8 五路线和 lead2/slot，只在第 10/17/24 天减半动物品 SELL。",
        "检验 audited topdays 是否能压低 V8 大批量路线的尾部风险。",
        transforms=("animal_half_topdays",),
    ),
    "v5_price_slot": _variant(
        "v5_price_slot",
        "baseline_v5",
        "v5_rule_hybrid+price_slot",
        "不改 SELL 集合和数量；把 premium 且实时价格/基准价更高的 SELL 放入更早的既有 SELL 槽位。",
        "减少高价值产品被同回合对手订单先行压价的暴露。",
        transforms=("premium_price_slot",),
    ),
    "v8_lead1": _variant(
        "v8_lead1",
        "baseline_v8",
        "v8_kawa+lead1_ablation",
        "把 V8 premium preempt 视野从两回合缩短到一回合，其余完整路径不变。",
        "减少对两回合后静态计划的依赖，同时保留最近一回合的抢先出售。",
        module_overrides=(("_PREEMPT_HORIZON", 1),),
    ),
    "v8_no_preempt": _variant(
        "v8_no_preempt",
        "baseline_v8",
        "v8_kawa+no_preempt_ablation",
        "关闭 V8 的跨回合 premium preempt；保留五路线、slot 和全部安全守卫。",
        "测量 preempt 的真实边际贡献，并避免克隆识别误触发造成的提前抛售。",
        module_overrides=(("_PREEMPT_ENABLED", False),),
    ),
    "v8_conservative": _variant(
        "v8_conservative",
        "baseline_v8",
        "v8_kawa+conservative_preempt",
        "保留 lead2，但每次最多 12、倍率 1.0、价格至少基准价 65%、克隆距离至多 3。",
        "保留高度相似对手下的抢跑收益，并限制过量或低价提前出售的尾部损失。",
        module_overrides=(
            ("_PREEMPT_FRACTION", 1.0),
            ("_PREEMPT_MAX_BATCH", 12),
            ("_PREEMPT_MIN_PRICE_RATIO", 0.65),
            ("_PREEMPT_MAX_CLONE_DISTANCE", 3),
        ),
    ),
}


EXPERT_SPECS: dict[str, ExpertSpec] = {**BASELINE_SPECS, **VARIANT_SPECS}
ALIASES = {
    "v1": "baseline_v1",
    "v2": "baseline_v2",
    "v5": "baseline_v5",
    "v8": "baseline_v8",
}


def resolve_spec(spec: str | ExpertSpec | Mapping[str, Any]) -> ExpertSpec:
    """Resolve exact IDs, legacy aliases, or an unambiguous ID prefix."""
    if isinstance(spec, ExpertSpec):
        return spec
    if isinstance(spec, Mapping):
        expert_id = str(spec.get("model_id", spec.get("expert_id", "")))
    else:
        expert_id = str(spec)
    key = expert_id.strip().lower()
    key = ALIASES.get(key, key)
    if key in EXPERT_SPECS:
        return EXPERT_SPECS[key]
    matches = [item for name, item in EXPERT_SPECS.items() if name.startswith(key)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise KeyError(f"unknown expert: {expert_id}")
    raise ValueError(f"ambiguous expert prefix {expert_id!r}: {[item.model_id for item in matches]}")


def _exec_module(path: Path, name: str) -> ModuleType:
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"unable to load expert source: {path}")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[name] = module
    try:
        module_spec.loader.exec_module(module)
        return module
    finally:
        # The returned module/function globals keep everything they need.  Do
        # not retain one large embedded action module per evaluated game.
        sys.modules.pop(name, None)


def _load_v5_isolated(source_dir: Path, namespace: str) -> ModuleType:
    dependency_paths = {
        "base_agent": source_dir / "base_agent.py",
        "v1_fallback": source_dir / "v1_fallback.py",
        "routes": source_dir / "routes.py",
    }
    previous = {name: sys.modules.get(name, _MISSING) for name in dependency_paths}
    try:
        for bare_name, path in dependency_paths.items():
            module = _exec_module(path, f"{namespace}_{bare_name}")
            sys.modules[bare_name] = module
        return _exec_module(source_dir / "main.py", f"{namespace}_main")
    finally:
        for bare_name, old in previous.items():
            if old is _MISSING:
                sys.modules.pop(bare_name, None)
            else:
                sys.modules[bare_name] = old


def _load_source(spec: ExpertSpec) -> ModuleType:
    source = MODEL_ROOT / spec.source
    if not source.is_file():
        raise FileNotFoundError(source)
    sequence = next(_MODULE_SEQUENCE)
    namespace = f"_kaggriculture_v10_{spec.model_id}_{sequence}"
    with _LOAD_LOCK:
        if spec.parent == "baseline_v5" or spec.model_id == "baseline_v5":
            module = _load_v5_isolated(source.parent, namespace)
        else:
            module = _exec_module(source, f"{namespace}_main")
    for name, value in spec.module_overrides:
        if not hasattr(module, name):
            raise AttributeError(f"{spec.model_id}: source has no override target {name}")
        setattr(module, name, value)
    return module


def _accepts_configuration(agent: Callable[..., Any]) -> bool:
    try:
        signature = inspect.signature(agent)
    except (TypeError, ValueError):
        return False
    return len(signature.parameters) >= 2


class RegisteredAgent:
    """Callable complete agent with attached immutable experiment metadata."""

    def __init__(self, spec: ExpertSpec) -> None:
        self.spec = spec
        self.module = _load_source(spec)
        self._agent = self.module.agent
        self._with_configuration = _accepts_configuration(self._agent)

    def __call__(self, obs: Any, configuration: Any = None) -> dict[str, Any]:
        if self._with_configuration:
            action = self._agent(obs, configuration)
        else:
            action = self._agent(obs)
        if self.spec.transforms:
            return apply_transforms(action, obs, self.spec.transforms)
        return action


def create_agent(spec: str | ExpertSpec | Mapping[str, Any]) -> RegisteredAgent:
    """Create a fresh, module-isolated callable for one registered expert."""
    return RegisteredAgent(resolve_spec(spec))


# Evaluators that consume a generic registry interface may use either name.
factory = create_agent


def registry_records() -> list[dict[str, Any]]:
    """JSON-friendly records consumable by the generic V10 agent factory."""
    records = []
    for name in sorted(EXPERT_SPECS):
        spec = EXPERT_SPECS[name]
        record = spec.as_record()
        record.update({
            "id": spec.model_id,
            "kind": "python",
            "path": "expert_registry.py",
            "factory": "create_agent",
            "factory_args": [spec.model_id],
            "tags": [spec.tag],
        })
        records.append(record)
    return records
