"""Isolated agent construction for the V10 replay/LOLO evaluation.

The historical Kaggriculture agents are ordinary ``main.py`` modules and many
of them keep episode state in module globals.  Reusing one imported module
across games therefore contaminates the next game.  This module always imports
a fresh module for every agent instance and removes its short dependency names
from ``sys.modules`` after construction.

Registry schema (paths are relative to the registry file)::

    {
      "models": [
        {"id": "v1", "kind": "python", "path": "../v1/main.py",
         "entrypoint": "agent", "family": "rule", "lineage": "v1"},
        {"id": "variant", "kind": "python", "path": "variant/main.py",
         "factory": "create_agent", "factory_kwargs": {"mode": "safe"}},
        {"id": "rule_router", "kind": "router", "router_kind": "rule",
         "experts": ["v1", "v2"], "anchor": "v1", "switch_step": 72}
      ]
    }

``models`` may also be an ``id -> spec`` mapping.  A Python module that exports
``create_agent`` is supported without an explicit ``factory`` field, which is
the contract used by V10 variants.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable, Mapping


HERE = Path(__file__).resolve().parent


@dataclass
class Registry:
    path: Path
    models: dict[str, dict[str, Any]]
    raw: dict[str, Any]

    def require(self, model_id: str) -> dict[str, Any]:
        try:
            return self.models[str(model_id)]
        except KeyError as exc:
            raise KeyError(f"unknown model id: {model_id}") from exc


class AgentHandle:
    """Callable wrapper retaining the imported module and stable metadata."""

    def __init__(self, model_id: str, spec: Mapping[str, Any], agent: Callable, module: Any = None):
        if not callable(agent):
            raise TypeError(f"agent for {model_id} is not callable")
        self.model_id = str(model_id)
        self.spec = dict(spec)
        self.agent = agent
        self.module = module
        # Decide the call contract once.  Retrying an agent after catching a
        # TypeError is unsafe: a stateful policy may already have advanced its
        # episode state before raising, so a second invocation corrupts the
        # trajectory and can hide the original defect.
        try:
            signature = inspect.signature(agent)
            try:
                signature.bind(None, None)
                self._accepts_configuration = True
            except TypeError:
                self._accepts_configuration = False
        except (TypeError, ValueError):
            self._accepts_configuration = bool(
                self.spec.get("accepts_configuration", False)
            )

    def __call__(self, obs: Any, configuration: Any = None):
        if self._accepts_configuration:
            return self.agent(obs, configuration)
        return self.agent(obs)

    def diagnostics(self) -> dict[str, Any]:
        method = getattr(self.agent, "diagnostics", None)
        if callable(method):
            return dict(method())
        method = getattr(self.module, "model_status", None)
        if callable(method):
            try:
                return {"model_status": method()}
            except Exception as exc:  # diagnostics must never break a game
                return {"diagnostic_error": f"{type(exc).__name__}: {exc}"}
        return {}


def load_registry(path: str | Path) -> Registry:
    path = Path(path).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        raw: dict[str, Any] = {"models": payload}
    elif isinstance(payload, dict):
        raw = payload
    else:
        raise ValueError("registry must be a JSON object or list")
    source = raw.get("models", raw.get("agents", {}))
    models: dict[str, dict[str, Any]] = {}
    if isinstance(source, list):
        for row in source:
            if not isinstance(row, dict) or not row.get("id"):
                raise ValueError("each registry model needs an id")
            models[str(row["id"])] = dict(row)
    elif isinstance(source, dict):
        for key, value in source.items():
            if not isinstance(value, dict):
                raise ValueError(f"invalid registry model: {key}")
            models[str(key)] = {"id": str(key), **dict(value)}
    else:
        raise ValueError("registry models must be a list or mapping")
    if not models:
        raise ValueError("empty model registry")
    for model_id, spec in models.items():
        spec.setdefault("id", model_id)
        spec.setdefault("family", model_id)
        spec.setdefault("lineage", spec["family"])
        spec.setdefault("tags", [spec["tag"]] if spec.get("tag") else [])
    return Registry(path=path, models=models, raw=raw)


def resolve_path(registry: Registry, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (registry.path.parent / path).resolve()


def _local_module_names(path: Path, spec: Mapping[str, Any]) -> set[str]:
    names = {"main"}
    names.update(item.stem for item in path.parent.glob("*.py") if item.stem != "__init__")
    names.update(str(item) for item in (spec.get("isolate_modules") or []))
    # These short names recur throughout V1--V9 and are particularly dangerous
    # when different historical agents are constructed in one worker process.
    names.update({"base_agent", "routes", "v1_fallback", "features", "catalog", "experts", "router"})
    return names


def _fresh_module(path: Path, model_id: str, spec: Mapping[str, Any]):
    if not path.is_file():
        raise FileNotFoundError(path)
    isolated = _local_module_names(path, spec)
    saved = {key: sys.modules.pop(key) for key in isolated if key in sys.modules}
    old_path = list(sys.path)
    unique = f"v10_agent_{model_id}_{os.getpid()}_{time.time_ns()}"
    try:
        sys.path.insert(0, str(path.parent))
        module_spec = importlib.util.spec_from_file_location(unique, path)
        if module_spec is None or module_spec.loader is None:
            raise RuntimeError(f"unable to import {path}")
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[unique] = module
        module_spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = old_path
        sys.modules.pop(unique, None)
        for key in isolated:
            sys.modules.pop(key, None)
        sys.modules.update(saved)


def _python_agent(registry: Registry, spec: Mapping[str, Any]) -> AgentHandle:
    model_id = str(spec["id"])
    path_value = spec.get("path") or spec.get("module_path")
    if not path_value:
        raise ValueError(f"python model {model_id} has no path")
    module = _fresh_module(resolve_path(registry, path_value), model_id, spec)
    kwargs = dict(spec.get("factory_kwargs") or spec.get("create_kwargs") or {})
    args = list(spec.get("factory_args") or [])
    factory_name = spec.get("factory")
    if factory_name:
        factory = getattr(module, str(factory_name))
        agent = factory(*args, **kwargs)
    elif callable(getattr(module, "create_agent", None)):
        agent = module.create_agent(*args, **kwargs)
    else:
        entrypoint = str(spec.get("entrypoint") or "agent")
        agent = getattr(module, entrypoint)
    return AgentHandle(model_id, spec, agent, module)


def _builtin_agent(spec: Mapping[str, Any]) -> AgentHandle:
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg

    name = str(spec.get("builtin") or spec.get("name") or spec.get("id"))
    choices = {"starter": kg.starter_agent, "random": kg.random_agent}
    if name not in choices:
        raise ValueError(f"unsupported builtin Kaggriculture agent: {name}")
    return AgentHandle(str(spec["id"]), spec, choices[name])


def create_agent(registry: Registry, model: str | Mapping[str, Any], _stack: tuple[str, ...] = ()) -> AgentHandle:
    """Construct one clean episode-local agent from a baseline or variant spec."""
    spec = registry.require(str(model)) if isinstance(model, str) else dict(model)
    model_id = str(spec.get("id") or "anonymous")
    if model_id in _stack:
        raise ValueError(f"recursive router registry reference: {' -> '.join((*_stack, model_id))}")
    kind = str(spec.get("kind") or ("router" if spec.get("router_kind") else "python"))
    if kind in {"python", "baseline", "variant"}:
        return _python_agent(registry, spec)
    if kind == "builtin":
        return _builtin_agent(spec)
    if kind == "router":
        # Lazy import avoids an agent_factory <-> router import cycle.
        try:
            from .router import create_router
        except ImportError:  # direct-script compatibility
            from router import create_router

        agent = create_router(registry, spec, stack=(*_stack, model_id))
        return AgentHandle(model_id, spec, agent)
    raise ValueError(f"unsupported model kind {kind!r} for {model_id}")


def registry_fingerprint(registry: Registry) -> str:
    import hashlib

    canonical = json.dumps(registry.raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8"))
    paths: set[Path] = set()
    for spec in registry.models.values():
        if spec.get("path") or spec.get("module_path"):
            module = resolve_path(registry, spec.get("path") or spec.get("module_path"))
            paths.add(module)
        source = spec.get("source")
        if source:
            candidates = [
                (registry.path.parent / str(source)).resolve(),
                (registry.path.parent.parent / str(source)).resolve(),
            ]
            for candidate in candidates:
                if candidate.is_file():
                    paths.add(candidate)
                    break
        for value in spec.get("code_paths") or []:
            paths.add(resolve_path(registry, value))
        weights = spec.get("weights")
        if weights:
            paths.add(resolve_path(registry, weights))
    for path in sorted(paths):
        digest.update(str(path).encode("utf-8"))
        if not path.is_file():
            digest.update(b"<missing>")
            continue
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
    return digest.hexdigest()
