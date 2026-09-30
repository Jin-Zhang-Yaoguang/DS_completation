#!/usr/bin/env python3
"""Freeze the 12 fixed experts and two step-72 Routers into one registry.

This command is run only after train/validation fitting.  It never reads the
official test manifest or a test result.  The learned weights, training report,
serving source paths and Router rule are hashed into the emitted registry so a
later pairwise resume cannot silently mix policy versions.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

try:
    from .agent_factory import load_registry, registry_fingerprint
    from .freeze_test_panel import (
        build_payload as build_test_panel_payload,
        validate_payload as validate_test_panel,
    )
    from .freeze_router_fit_sources import validate_payload as validate_fit_exclusions
    from .pairwise_evaluate import load_seed_manifest
    from .router import FEATURE_DIM, FEATURE_NAMES, FEATURE_SCHEMA, ROUTER_WEIGHT_SCHEMA
    from .train_router import training_implementation_fingerprint
except ImportError:  # direct-file CLI compatibility
    from agent_factory import load_registry, registry_fingerprint
    from freeze_test_panel import (
        build_payload as build_test_panel_payload,
        validate_payload as validate_test_panel,
    )
    from freeze_router_fit_sources import validate_payload as validate_fit_exclusions
    from pairwise_evaluate import load_seed_manifest
    from router import FEATURE_DIM, FEATURE_NAMES, FEATURE_SCHEMA, ROUTER_WEIGHT_SCHEMA
    from train_router import training_implementation_fingerprint


HERE = Path(__file__).resolve().parent
SCHEMA = "kaggriculture-v10-final-registry-1"
DEFAULT_EXPERTS = ("baseline_v1", "baseline_v2", "baseline_v5", "baseline_v8")
FIXED_MODEL_IDS = (
    "baseline_v1", "baseline_v2", "baseline_v5", "baseline_v8",
    "v1_topdays", "v2_topdays", "v5_topdays", "v8_topdays",
    "v5_price_slot", "v8_lead1", "v8_no_preempt", "v8_conservative",
)
TRAINING_SCHEMA = "kaggriculture-v10-learned-router-training-1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path, parent: Path) -> str:
    return os.path.relpath(path.resolve(), parent.resolve())


def _rebase_spec(spec: Mapping[str, Any], source_parent: Path, output_parent: Path) -> dict[str, Any]:
    result = deepcopy(dict(spec))
    for key in ("path", "module_path", "weights"):
        value = result.get(key)
        if value:
            path = Path(str(value)).expanduser()
            resolved = path.resolve() if path.is_absolute() else (source_parent / path).resolve()
            result[key] = _relative(resolved, output_parent)
    if result.get("code_paths"):
        rebased = []
        for value in result["code_paths"]:
            path = Path(str(value)).expanduser()
            resolved = path.resolve() if path.is_absolute() else (source_parent / path).resolve()
            rebased.append(_relative(resolved, output_parent))
        result["code_paths"] = rebased
    return result


def _validate_training_report(report: Mapping[str, Any], experts: Sequence[str]) -> str:
    if report.get("schema") != TRAINING_SCHEMA:
        raise ValueError("unexpected learned Router training-report schema")
    if list(report.get("fit_splits") or []) != ["train", "validation"]:
        raise ValueError("training report must be fit on train+validation only")
    if report.get("test_used_for_fit") is not False:
        raise ValueError("training report does not prove test_used_for_fit=false")
    if report.get("pre_selection_test_access") is not False:
        raise ValueError("training report does not prove pre_selection_test_access=false")
    if int((report.get("rows") or {}).get("test_seen", -1)) != 0:
        raise ValueError("training report saw test rows")
    if (report.get("rows") or {}) != {
        "all": 6400,
        "train": 3200,
        "validation": 3200,
        "test_seen": 0,
    }:
        raise ValueError("training report does not contain the exact formal grid")
    formal = report.get("formal_grid_audit") or {}
    if formal.get("required") is not True or formal.get("passed") is not True:
        raise ValueError("training report did not pass the formal 6,400-row grid gate")
    if not all((formal.get("checks") or {}).values()):
        raise ValueError("training report formal grid checks are incomplete")
    if report.get("training_implementation_sha256") != training_implementation_fingerprint():
        raise ValueError("training report implementation differs from current trainer")
    if len(str(report.get("registry_and_code_sha256") or "")) != 64:
        raise ValueError("training report lacks a registry/code fingerprint")
    classes = [str(item) for item in (report.get("classes") or [])]
    if classes != [str(item) for item in experts]:
        raise ValueError(f"training classes differ from frozen experts: {classes}")
    rank = [str(item) for item in (report.get("best_fixed_rank") or [])]
    if set(rank) != set(classes) or not rank:
        raise ValueError("training report has no complete frozen fixed-expert rank")
    fingerprints = report.get("run_fingerprints_by_split") or {}
    if set(fingerprints) != {"train", "validation"}:
        raise ValueError("training report has unexpected fit split fingerprints")
    values = [str(item) for split in ("train", "validation") for item in fingerprints[split]]
    if len(values) != 2 or len(set(values)) != 1 or len(values[0]) != 64:
        raise ValueError("train/validation must share one exact collection fingerprint")
    support = {str(key): int(value) for key, value in (report.get("final_support") or {}).items()}
    if support != {model_id: 1600 for model_id in classes}:
        raise ValueError(f"unexpected final Router support: {support}")
    lolo = report.get("leave_one_root_lineage_out") or {}
    if set(lolo) != set(classes):
        raise ValueError("LOLO report does not hold out every root lineage exactly once")
    for lineage, fold in lolo.items():
        if (
            fold.get("held_root_lineage") != lineage
            or fold.get("held_lineage_absent_from_training_opponents") is not True
            or int(fold.get("train_rows") or -1) != 2400
            or int(fold.get("evaluation_rows") or -1) != 800
            or int((fold.get("comparison") or {}).get("contexts") or -1) != 200
        ):
            raise ValueError(f"incomplete LOLO fold: {lineage}")
    validation = report.get("validation_comparison_train_only_fit") or {}
    if int(validation.get("contexts") or -1) != 800 or int(
        validation.get("independent_seed_clusters") or -1
    ) != 100:
        raise ValueError("train-only validation comparison is incomplete")
    return rank[0]


def _validate_weights(path: Path, experts: Sequence[str]) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    with np.load(path, allow_pickle=False) as data:
        if str(data["schema"].item()) != ROUTER_WEIGHT_SCHEMA:
            raise ValueError("learned Router weight schema mismatch")
        if str(data["feature_schema"].item()) != FEATURE_SCHEMA:
            raise ValueError("learned Router feature schema mismatch")
        classes = [str(item) for item in data["classes"].tolist()]
        if classes != [str(item) for item in experts]:
            raise ValueError(f"weight classes differ from frozen experts: {classes}")
        feature_names = [str(item) for item in data["feature_names"].tolist()]
        if feature_names != list(FEATURE_NAMES):
            raise ValueError("learned Router feature names differ from serving")
        mean = np.asarray(data["mean"])
        scale = np.asarray(data["scale"])
        coef = np.asarray(data["coef"])
        intercept = np.asarray(data["intercept"])
        if mean.shape != (FEATURE_DIM,) or scale.shape != (FEATURE_DIM,):
            raise ValueError("invalid learned Router normalisation shape")
        if coef.shape != (FEATURE_DIM, len(experts)) or intercept.shape != (len(experts),):
            raise ValueError("invalid learned Router head shape")
        if not all(np.all(np.isfinite(value)) for value in (mean, scale, coef, intercept)):
            raise ValueError("non-finite learned Router weights")
        if np.any(scale <= 0):
            raise ValueError("non-positive learned Router scale")


def build_registry(
    fixed_registry_path: Path,
    training_report_path: Path,
    weights_path: Path,
    output_path: Path,
    experts: Sequence[str] = DEFAULT_EXPERTS,
    test_panel_path: Path = HERE / "final_test_panel.json",
    quarantine_path: Path = HERE / "test_exposure_quarantine.json",
    fit_exclusions_path: Path = HERE / "router_fit_source_exclusions.json",
) -> dict[str, Any]:
    fixed_registry_path = fixed_registry_path.expanduser().resolve()
    training_report_path = training_report_path.expanduser().resolve()
    weights_path = weights_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    test_panel_path = test_panel_path.expanduser().resolve()
    quarantine_path = quarantine_path.expanduser().resolve()
    fit_exclusions_path = fit_exclusions_path.expanduser().resolve()
    experts = tuple(str(item) for item in experts)

    fixed = load_registry(fixed_registry_path)
    if tuple(fixed.models) != FIXED_MODEL_IDS:
        raise ValueError(
            "final matrix requires the exact pre-registered 12 fixed experts in frozen order"
        )
    for model_id in experts:
        fixed.require(model_id)

    report = json.loads(training_report_path.read_text(encoding="utf-8"))
    best_fixed = _validate_training_report(report, experts)
    _validate_weights(weights_path, experts)
    if Path(str(report.get("weights") or "")).expanduser().resolve() != weights_path:
        raise ValueError("training report points to a different learned weight file")
    weights_hash = _sha256(weights_path)
    if report.get("weights_sha256") != weights_hash:
        raise ValueError("learned weights do not match the training report")
    if report.get("registry_and_code_sha256") != registry_fingerprint(
        load_registry(HERE / "router_training_registry.json")
    ):
        raise ValueError("training report registry/code fingerprint is stale")
    rule = deepcopy(report.get("frozen_rule_spec") or {})
    if not isinstance(rule.get("rule"), Mapping):
        raise ValueError("training report has no frozen rule Router specification")
    panel_payload = json.loads(test_panel_path.read_text(encoding="utf-8"))
    source_manifest = Path(str(panel_payload.get("source_manifest") or ""))
    validate_test_panel(panel_payload, source_manifest, quarantine_path)
    expected_panel_payload = build_test_panel_payload(source_manifest, quarantine_path)
    for key in (
        "source_manifest_sha256", "quarantine_file_sha256",
        "clean_pool_records_sha256", "records_sha256", "selection",
    ):
        if panel_payload.get(key) != expected_panel_payload.get(key):
            raise ValueError(f"frozen test panel cannot be reproduced: {key}")
    quarantine_hash = _sha256(quarantine_path)
    panel_file_hash = _sha256(test_panel_path)
    if panel_payload.get("quarantine_file_sha256") != quarantine_hash:
        raise ValueError("frozen test panel is bound to a different quarantine")
    manifest_records = load_seed_manifest(source_manifest)
    manifest_splits = Counter(str(item.split) for item in manifest_records)
    manifest_dates_by_split = {
        split: dict(
            sorted(
                Counter(
                    item.date for item in manifest_records if item.split == split
                ).items()
            )
        )
        for split in sorted(manifest_splits)
    }
    if (
        len(manifest_records) != 2090
        or len({int(item.seed) for item in manifest_records}) != 2090
        or set(item.date for item in manifest_records)
        != {"2026-08-18", "2026-08-19", "2026-08-20"}
        or set(manifest_splits) != {"train", "validation", "test"}
    ):
        raise ValueError("canonical evaluation seed manifest shape changed")
    fit_exclusions = json.loads(fit_exclusions_path.read_text(encoding="utf-8"))
    fit_grid_path = Path(str(fit_exclusions.get("source_grid") or "")).expanduser().resolve()
    fit_seeds = validate_fit_exclusions(fit_exclusions, fit_grid_path)
    collection_values = {
        value
        for values in (report.get("run_fingerprints_by_split") or {}).values()
        for value in values
    }
    if collection_values != {fit_exclusions.get("collection_fingerprint")}:
        raise ValueError("Router fit exclusions differ from the training collection")
    if fit_exclusions.get("registry_and_code_sha256") != report.get(
        "registry_and_code_sha256"
    ):
        raise ValueError("Router fit exclusions differ from the training registry/code")

    output_parent = output_path.parent
    models = [
        _rebase_spec(spec, fixed_registry_path.parent, output_parent)
        for spec in fixed.models.values()
    ]
    router_source = _relative(HERE / "router.py", output_parent)
    common = {
        "kind": "router",
        "experts": list(experts),
        "anchor": "baseline_v1",
        "switch_step": 72,
        "code_paths": [router_source],
        "lineage": ["v10_step72_router"],
        "family": "v10_step72_full_expert_router",
    }
    rule_model = {
        "id": "rule_router",
        **common,
        "router_kind": "rule",
        "rule": deepcopy(rule["rule"]),
        "tags": ["router", "rule", "frozen_train_validation"],
    }
    learned_model = {
        "id": "learned_router",
        **common,
        "router_kind": "learned",
        "weights": _relative(weights_path, output_parent),
        "tags": ["router", "learned", "numpy", "frozen_train_validation"],
    }
    models.extend([rule_model, learned_model])
    payload = {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sealed_before_test": True,
        "test_used_for_fit": False,
        "pre_selection_test_access": False,
        "fixed_registry_sha256": registry_fingerprint(fixed),
        "training_report_sha256": _sha256(training_report_path),
        "training_report_schema": report.get("schema"),
        "training_implementation_sha256": report.get(
            "training_implementation_sha256"
        ),
        "learned_weights_sha256": weights_hash,
        "best_fixed_model": best_fixed,
        "router_experts": list(experts),
        "source_manifest_seal": {
            "path": str(source_manifest.resolve()),
            "file_sha256": panel_payload["source_manifest_sha256"],
            "records": len(manifest_records),
            "unique_seeds": len({int(item.seed) for item in manifest_records}),
            "dates": ["2026-08-18", "2026-08-19", "2026-08-20"],
            "split_counts": dict(sorted(manifest_splits.items())),
            "date_counts_by_split": manifest_dates_by_split,
        },
        "fit_protocol": {
            "fit_splits": ["train", "validation"],
            "test_used_for_fit": False,
            "pre_selection_test_access": False,
            "formal_grid_rows": 6400,
            "formal_grid_contexts": 1600,
            "collection_fingerprint": fit_exclusions.get(
                "collection_fingerprint"
            ),
            "registry_and_code_sha256": fit_exclusions.get(
                "registry_and_code_sha256"
            ),
            "source_grid_file_sha256": fit_exclusions.get(
                "source_grid_file_sha256"
            ),
            "training_schema": report.get("schema"),
            "weight_schema": ROUTER_WEIGHT_SCHEMA,
            "feature_schema": FEATURE_SCHEMA,
        },
        "router_fit_source_exclusions": {
            "path": str(fit_exclusions_path),
            "file_sha256": _sha256(fit_exclusions_path),
            "schema": fit_exclusions.get("schema"),
            "records": len(fit_seeds),
            "records_sha256": fit_exclusions.get("records_sha256"),
            "collection_fingerprint": fit_exclusions.get("collection_fingerprint"),
            "registry_and_code_sha256": fit_exclusions.get(
                "registry_and_code_sha256"
            ),
            "source_grid_file_sha256": fit_exclusions.get(
                "source_grid_file_sha256"
            ),
            "league_must_exclude": True,
        },
        "test_protocol": {
            "sealed_before_test": True,
            "historical_outcomes_used_for_selection": False,
            "panel_schema": panel_payload.get("schema"),
            "quarantine_schema": panel_payload.get("quarantine_schema"),
            "source_manifest": str(source_manifest.resolve()),
            "source_manifest_sha256": panel_payload["source_manifest_sha256"],
            "quarantine": str(quarantine_path),
            "quarantine_file_sha256": quarantine_hash,
            "quarantined_sources": 42,
            "clean_test_sources": 168,
            "clean_pool_records_sha256": panel_payload["clean_pool_records_sha256"],
            "frozen_panel": str(test_panel_path),
            "frozen_panel_file_sha256": panel_file_hash,
            "frozen_panel_records_sha256": panel_payload["records_sha256"],
            "panel_sources": 100,
            "date_quota": panel_payload["selection"]["date_quota"],
            "salt": panel_payload["selection"]["salt"],
            "games_per_pair": 200,
            "unordered_pairs": 91,
            "expected_games": 18200,
            "model_ids": [str(model["id"]) for model in models],
        },
        "models": models,
    }
    output_parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output_path)

    emitted = load_registry(output_path)
    if len(emitted.models) != 14:
        raise AssertionError("emitted final registry does not contain 14 models")
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed-registry", type=Path, default=HERE / "fixed_registry.json")
    parser.add_argument("--training-report", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "final_registry.json")
    parser.add_argument("--experts", nargs="+", default=list(DEFAULT_EXPERTS))
    parser.add_argument("--test-panel", type=Path, default=HERE / "final_test_panel.json")
    parser.add_argument("--quarantine", type=Path, default=HERE / "test_exposure_quarantine.json")
    parser.add_argument(
        "--fit-exclusions",
        type=Path,
        default=HERE / "router_fit_source_exclusions.json",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_registry(
        args.fixed_registry, args.training_report, args.weights, args.output,
        args.experts, args.test_panel, args.quarantine, args.fit_exclusions,
    )
    registry = load_registry(args.output)
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "models": len(registry.models),
                "best_fixed_model": payload["best_fixed_model"],
                "registry_and_code_sha256": registry_fingerprint(registry),
                "sealed_before_test": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
