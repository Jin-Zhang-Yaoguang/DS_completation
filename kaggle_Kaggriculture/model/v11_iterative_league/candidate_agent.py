"""Complete parent-agent wrapper used by V11 pending candidates."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping

try:
    from .mutation_catalog import apply_mutation
except ImportError:  # Loaded as an isolated file by the V10 agent factory.
    from mutation_catalog import apply_mutation


HERE = Path(__file__).resolve().parent
V10_FACTORY = HERE.parent / "v10_replay_lolo_router" / "agent_factory.py"


def _load_parent(parent_registry: str | Path, parent_id: str):
    registry_path = Path(parent_registry).expanduser()
    if not registry_path.is_absolute():
        registry_path = (HERE / registry_path).resolve()
    module_name = f"_v11_parent_factory_{hashlib.sha256(str(registry_path).encode()).hexdigest()[:12]}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, V10_FACTORY)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load V10 agent factory: {V10_FACTORY}")
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    sys.modules[module_name] = module
    try:
        sys.path.insert(0, str(V10_FACTORY.parent))
        spec.loader.exec_module(module)
        registry = module.load_registry(registry_path)
        return module.create_agent(registry, str(parent_id))
    finally:
        sys.path[:] = old_path
        sys.modules.pop(module_name, None)


class ResidualCandidate:
    """A full episode-local parent policy followed by one market residual."""

    def __init__(
        self,
        parent_registry: str | Path,
        parent_id: str,
        mutation_name: str,
        mutation_params: Mapping[str, Any] | None = None,
        candidate_id: str = "pending_candidate",
    ) -> None:
        self.candidate_id = str(candidate_id)
        self.parent_id = str(parent_id)
        self.mutation_name = str(mutation_name)
        self.mutation_params = dict(mutation_params or {})
        self.parent = _load_parent(parent_registry, self.parent_id)
        self.calls = 0
        self.changed_actions = 0

    def __call__(self, obs: Any, configuration: Any = None):
        before = self.parent(obs, configuration)
        after = apply_mutation(
            self.mutation_name, before, obs, self.mutation_params
        )
        self.calls += 1
        if json.dumps(before, sort_keys=True, separators=(",", ":")) != json.dumps(
            after, sort_keys=True, separators=(",", ":")
        ):
            self.changed_actions += 1
        return after

    def diagnostics(self) -> dict[str, Any]:
        parent_method = getattr(self.parent, "diagnostics", None)
        parent_diagnostics = (
            dict(parent_method()) if callable(parent_method) else {}
        )
        return {
            "kind": "v11_complete_parent_market_residual",
            "candidate_id": self.candidate_id,
            "parent_id": self.parent_id,
            "mutation": self.mutation_name,
            "calls": self.calls,
            "changed_actions": self.changed_actions,
            # Preserve the complete serving ancestry.  A FastRouter parent may
            # be wrapped by several residual candidates; runtime/prefix errors
            # must remain visible to league and terminal integrity gates.
            "parent_diagnostics": parent_diagnostics,
        }


def create_agent(
    parent_registry: str | Path,
    parent_id: str,
    mutation_name: str,
    mutation_params: Mapping[str, Any] | None = None,
    candidate_id: str = "pending_candidate",
) -> ResidualCandidate:
    return ResidualCandidate(
        parent_registry=parent_registry,
        parent_id=parent_id,
        mutation_name=mutation_name,
        mutation_params=mutation_params,
        candidate_id=candidate_id,
    )
