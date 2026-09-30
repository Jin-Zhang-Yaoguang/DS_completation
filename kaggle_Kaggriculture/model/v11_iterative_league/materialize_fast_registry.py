#!/usr/bin/env python3
"""把已通过正式等价门禁的 V10 Router 物化为 FastShadowRouter 代理。"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .league import HERE, _atomic_json, _canonical, model_fingerprints
    from .verify_fast_router import validate_formal_report
    from .audit_fast_router_challenge import validate_challenge_report
except ImportError:
    from league import HERE, _atomic_json, _canonical, model_fingerprints
    from verify_fast_router import validate_formal_report
    from audit_fast_router_challenge import validate_challenge_report

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    Registry,
    load_registry,
    registry_fingerprint,
    resolve_path,
)


SCHEMA = "kaggriculture-v11-fast-router-registry-1"


def _relative(path: Path, parent: Path) -> str:
    return os.path.relpath(path.resolve(), parent.resolve())


def _rebase_spec(
    spec: Mapping[str, Any], source_parent: Path, output_parent: Path
) -> dict[str, Any]:
    result = deepcopy(dict(spec))
    for key in ("path", "module_path", "weights"):
        value = result.get(key)
        if value:
            path = Path(str(value)).expanduser()
            resolved = path.resolve() if path.is_absolute() else (source_parent / path).resolve()
            result[key] = _relative(resolved, output_parent)
    if result.get("code_paths"):
        result["code_paths"] = [
            _relative(
                Path(str(value)).expanduser().resolve()
                if Path(str(value)).expanduser().is_absolute()
                else (source_parent / str(value)).resolve(),
                output_parent,
            )
            for value in result["code_paths"]
        ]
    return result


def _serving_paths(registry: Registry, spec: Mapping[str, Any]) -> set[Path]:
    result: set[Path] = set()
    for key in ("path", "module_path", "weights"):
        if spec.get(key):
            result.add(resolve_path(registry, str(spec[key])))
    for value in spec.get("code_paths") or []:
        result.add(resolve_path(registry, str(value)))
    return result


def _embedded_experts(registry: Registry, router_spec: Mapping[str, Any]) -> dict[str, Any]:
    result = {}
    for model_id in router_spec.get("experts") or []:
        model_id = str(model_id)
        spec = deepcopy(registry.require(model_id))
        if str(spec.get("kind") or "python") == "router":
            raise ValueError("nested routers are not supported by FastShadow materialization")
        result[model_id] = spec
    return result


def materialize(
    source_path: Path,
    output_path: Path,
    equivalence_report_path: Path | None = None,
    challenge_report_path: Path | None = None,
) -> dict[str, Any]:
    source_path = source_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    source = load_registry(source_path)
    is_formal_v10 = source.raw.get("schema") == "kaggriculture-v10-final-registry-1"
    if is_formal_v10 and equivalence_report_path is None:
        raise ValueError(
            "sealed V10 final registry requires --equivalence-report before materialization"
        )
    if is_formal_v10 and challenge_report_path is None:
        raise ValueError(
            "sealed V10 final registry requires --challenge-report before materialization"
        )
    formal_equivalence = (
        validate_formal_report(equivalence_report_path, source.path)
        if equivalence_report_path is not None
        else None
    )
    formal_challenge = (
        validate_challenge_report(
            challenge_report_path,
            equivalence_report_path,
            source.path,
        )
        if challenge_report_path is not None
        else None
    )
    output_parent = output_path.parent
    models = []
    converted = []
    for model_id, raw_spec in source.models.items():
        spec = deepcopy(raw_spec)
        kind = str(spec.get("kind") or ("router" if spec.get("router_kind") else "python"))
        if kind != "router":
            models.append(_rebase_spec(spec, source.path.parent, output_parent))
            continue
        embedded = _embedded_experts(source, spec)
        paths = {HERE / "fast_router.py"}
        paths.add(HERE.parent / "v10_replay_lolo_router" / "router.py")
        paths.add(HERE.parent / "v10_replay_lolo_router" / "agent_factory.py")
        paths.update(_serving_paths(source, spec))
        for expert_spec in embedded.values():
            paths.update(_serving_paths(source, expert_spec))
        metadata = {
            key: deepcopy(value)
            for key, value in spec.items()
            if key
            not in {
                "kind",
                "path",
                "module_path",
                "entrypoint",
                "factory",
                "factory_args",
                "factory_kwargs",
                "code_paths",
                "weights",
                "experts",
                "anchor",
                "switch_step",
                "router_kind",
                "rule",
            }
        }
        proxy = {
            **metadata,
            "id": model_id,
            "kind": "python",
            "path": _relative(HERE / "fast_router.py", output_parent),
            "factory": "create_agent",
            "factory_kwargs": {
                "router_spec": spec,
                "expert_specs": embedded,
                "registry_parent": str(source.path.parent),
            },
            "code_paths": [_relative(path, output_parent) for path in sorted(paths)],
            "fast_shadow": True,
            "source_router_spec_sha256": hashlib.sha256(_canonical(spec)).hexdigest(),
        }
        models.append(proxy)
        converted.append(model_id)
    # Preserve every pre-test seal/provenance field verbatim.  Only the schema,
    # source linkage and model serving entries are changed by materialisation.
    preserved = {
        key: deepcopy(value)
        for key, value in source.raw.items()
        if key not in {
            "schema",
            "models",
            "agents",
            "formal_fast_router_equivalence",
            "formal_fast_router_fresh_challenge",
            "materialized_serving_fingerprints",
        }
    }
    payload = {
        **preserved,
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_registry": str(source.path),
        "source_final_registry_sha256": hashlib.sha256(source.path.read_bytes()).hexdigest(),
        "source_registry_schema": source.raw.get("schema"),
        "source_registry_raw_sha256": hashlib.sha256(_canonical(source.raw)).hexdigest(),
        "source_registry_and_code_sha256": registry_fingerprint(source),
        "converted_routers": converted,
        "equivalence_contract": {
            "steps_0_through_switch": "all experts called; exact V10 prefix validation",
            "after_switch": "selected expert only",
            "normal_path": "action-equivalent to V10 ShadowRouter",
            "selected_exception": "explicit PASS; no stale-anchor fallback",
        },
        **(
            {"formal_fast_router_equivalence": formal_equivalence}
            if formal_equivalence is not None
            else {}
        ),
        **(
            {"formal_fast_router_fresh_challenge": formal_challenge}
            if formal_challenge is not None
            else {}
        ),
        "models": models,
    }
    provisional = Registry(
        path=output_path,
        models={str(item["id"]): item for item in models},
        raw=payload,
    )
    payload["materialized_serving_fingerprints"] = model_fingerprints(
        provisional, list(provisional.models)
    )
    _atomic_json(output_path, payload)
    emitted = load_registry(output_path)
    if list(emitted.models) != list(source.models):
        raise AssertionError("fast registry changed the sealed model IDs/order")
    if model_fingerprints(emitted, list(emitted.models)) != payload.get(
        "materialized_serving_fingerprints"
    ):
        raise AssertionError("materialized serving fingerprints cannot be reproduced")
    if is_formal_v10 and emitted.raw.get("formal_fast_router_equivalence") != formal_equivalence:
        raise AssertionError("formal FastRouter equivalence seal was not preserved")
    if is_formal_v10 and emitted.raw.get(
        "formal_fast_router_fresh_challenge"
    ) != formal_challenge:
        raise AssertionError("formal FastRouter fresh challenge seal was not preserved")
    for key in (
        "sealed_before_test",
        "test_used_for_fit",
        "pre_selection_test_access",
        "fixed_registry_sha256",
        "training_report_sha256",
        "learned_weights_sha256",
        "best_fixed_model",
        "router_experts",
        "test_protocol",
        "router_fit_source_exclusions",
    ):
        if key in source.raw and emitted.raw.get(key) != source.raw.get(key):
            raise AssertionError(f"fast registry changed sealed provenance field: {key}")
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--equivalence-report", type=Path)
    parser.add_argument("--challenge-report", type=Path)
    parser.add_argument("--output", type=Path, default=HERE / "fast_registry.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = materialize(
        args.source,
        args.output,
        args.equivalence_report,
        args.challenge_report,
    )
    emitted = load_registry(args.output)
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "models": len(payload["models"]),
                "converted_routers": payload["converted_routers"],
                "registry_and_code_sha256": registry_fingerprint(emitted),
                "sealed_before_test": emitted.raw.get("sealed_before_test"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
