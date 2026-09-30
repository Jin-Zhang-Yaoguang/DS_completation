"""V10 ShadowRouter 的行为等价快速执行路径。

边界前（含 step=72）仍调用全部专家，完整复现 prefix 校验和一次选择；选择后
只推进 chosen expert。正常执行时动作与 V10 ShadowRouter 完全一致。若 chosen
expert 抛出异常，本实现返回显式 PASS 并记录错误，而不使用已经停止同步、状态
陈旧的 anchor 冒充安全回退。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from agent_factory import (
    Registry,
    create_agent as create_registered_agent,
    resolve_path,
)
from router import (
    LearnedSelector,
    RuleSelector,
    ShadowRouter,
    _copy_action,
    _get,
)


class FastShadowRouter(ShadowRouter):
    """Match ShadowRouter, but stop advancing unselected experts after switch."""

    def _reset(self) -> None:
        super()._reset()
        self.runtime_errors: list[str] = []

    def __call__(self, obs: Any, configuration: Any = None):
        step = int(_get(obs, "step", 0) or 0)
        if step <= self.switch_step:
            return super().__call__(obs, configuration)
        if step < self.last_step:
            # A valid episode reset reaches step 0 and is handled by super.
            self._reset()
        self.last_step = step
        if self.selected is None or self.selected not in self.experts:
            self.runtime_errors.append(f"step={step}:RuntimeError:no_selected_expert")
            return {"farmer": ["PASS"], "hands": [], "market": []}
        try:
            return _copy_action(self.experts[self.selected](obs, configuration))
        except Exception as exc:
            self.runtime_errors.append(f"step={step}:{type(exc).__name__}:{exc}")
            # The anchor has not been advanced since the switch and therefore
            # cannot be a state-correct fallback. Make the failure observable.
            self.selected_fallbacks += 1
            return {"farmer": ["PASS"], "hands": [], "market": []}

    def diagnostics(self) -> dict[str, Any]:
        result = super().diagnostics()
        result["fast_shadow"] = True
        result["post_switch_policy"] = "selected_only"
        result["runtime_errors"] = list(self.runtime_errors)
        return result


def create_agent(
    router_spec: Mapping[str, Any],
    expert_specs: Mapping[str, Mapping[str, Any]],
    registry_parent: str,
) -> FastShadowRouter:
    """Factory used by a materialized Python proxy registry entry."""

    spec = dict(router_spec)
    models = {str(key): dict(value) for key, value in expert_specs.items()}
    registry = Registry(
        path=Path(registry_parent).expanduser().resolve() / "_v11_embedded_registry.json",
        models=models,
        raw={"models": list(models.values())},
    )
    expert_ids = [str(item) for item in (spec.get("experts") or [])]
    anchor = str(spec.get("anchor") or (expert_ids[0] if expert_ids else ""))
    if len(expert_ids) < 2 or anchor not in expert_ids:
        raise ValueError("fast router needs at least two experts and a valid anchor")
    experts = {
        model_id: create_registered_agent(registry, model_id) for model_id in expert_ids
    }
    kind = str(spec.get("router_kind") or "rule")
    if kind == "rule":
        selector = RuleSelector(spec, models, anchor)
    elif kind == "learned":
        weights = spec.get("weights")
        if not weights:
            raise ValueError("learned fast router has no weights")
        selector = LearnedSelector(resolve_path(registry, str(weights)), anchor)
    else:
        raise ValueError(f"unsupported fast router kind: {kind}")
    return FastShadowRouter(
        str(spec.get("id") or "fast_router"),
        experts,
        models,
        anchor,
        selector,
        int(spec.get("switch_step", 72)),
    )

