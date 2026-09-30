#!/usr/bin/env python3
"""Read-only audit of the V10 grid -> Router -> sealed 14-model chain.

The command never creates a Kaggle environment and never opens a final-test
game/result file.  Missing downstream artifacts are reported as explicit
blockers, which makes the same command useful both while the train/validation
grid is running and immediately before the one-time frozen test matrix.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .agent_factory import load_registry, registry_fingerprint
    from .audit_router_grid import audit_grid
    from .build_final_registry import (
        DEFAULT_EXPERTS,
        FIXED_MODEL_IDS,
        SCHEMA as FINAL_REGISTRY_SCHEMA,
        _rebase_spec,
        _validate_training_report,
        _validate_weights,
    )
    from .collect_router_grid import DEFAULT_DATES, DEFAULT_MODELS
    from .freeze_router_fit_sources import validate_payload as validate_fit_exclusions
    from .freeze_test_panel import (
        build_payload as build_test_panel_payload,
        validate_payload as validate_test_panel,
    )
except ImportError:  # direct-file CLI compatibility
    from agent_factory import load_registry, registry_fingerprint
    from audit_router_grid import audit_grid
    from build_final_registry import (
        DEFAULT_EXPERTS,
        FIXED_MODEL_IDS,
        SCHEMA as FINAL_REGISTRY_SCHEMA,
        _rebase_spec,
        _validate_training_report,
        _validate_weights,
    )
    from collect_router_grid import DEFAULT_DATES, DEFAULT_MODELS
    from freeze_router_fit_sources import validate_payload as validate_fit_exclusions
    from freeze_test_panel import (
        build_payload as build_test_panel_payload,
        validate_payload as validate_test_panel,
    )


HERE = Path(__file__).resolve().parent
SCHEMA = "kaggriculture-v10-freeze-chain-audit-1"
FINAL_MODEL_IDS = (*FIXED_MODEL_IDS, "rule_router", "learned_router")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def _logical_router_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    if spec.get("kind") == "router":
        return deepcopy(dict(spec))
    nested = ((spec.get("factory_kwargs") or {}).get("router_spec") or {})
    if spec.get("fast_shadow") is True and isinstance(nested, Mapping):
        return deepcopy(dict(nested))
    raise ValueError("model is not a logical Router or FastShadow proxy")


def audit_chain(
    *,
    grid_path: Path,
    grid_summary_path: Path,
    fixed_registry_path: Path,
    training_registry_path: Path,
    manifest_path: Path,
    quarantine_path: Path,
    test_panel_path: Path,
    fit_exclusions_path: Path,
    training_report_path: Path,
    weights_path: Path,
    final_registry_path: Path,
    fast_registry_path: Path,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    evidence: dict[str, Any] = {}
    blockers: list[str] = []

    def record(name: str, passed: bool, detail: Any = None) -> None:
        checks[name] = bool(passed)
        if detail is not None:
            evidence[name] = detail
        if not passed:
            blockers.append(name)

    fixed = load_registry(fixed_registry_path)
    training_registry = load_registry(training_registry_path)
    fixed_hash = registry_fingerprint(fixed)
    training_registry_hash = registry_fingerprint(training_registry)
    record(
        "fixed_registry_exact_12",
        tuple(fixed.models) == FIXED_MODEL_IDS,
        {"models": list(fixed.models), "registry_and_code_sha256": fixed_hash},
    )
    record(
        "router_training_registry_exact_4",
        tuple(training_registry.models) == tuple(DEFAULT_EXPERTS),
        {
            "models": list(training_registry.models),
            "registry_and_code_sha256": training_registry_hash,
        },
    )

    panel_payload = _read(test_panel_path)
    panel = validate_test_panel(panel_payload, manifest_path, quarantine_path)
    reproduced_panel = build_test_panel_payload(manifest_path, quarantine_path)
    panel_fields = (
        "source_manifest_sha256",
        "quarantine_file_sha256",
        "clean_pool_records_sha256",
        "records_sha256",
        "selection",
    )
    record(
        "test_panel_frozen_metadata_only_reproducible",
        len(panel) == 100
        and all(panel_payload.get(key) == reproduced_panel.get(key) for key in panel_fields),
        {
            "panel_file_sha256": _sha256(test_panel_path),
            "panel_records_sha256": panel_payload.get("records_sha256"),
            "clean_pool_records_sha256": panel_payload.get("clean_pool_records_sha256"),
            "quarantine_file_sha256": _sha256(quarantine_path),
            "date_quota": (panel_payload.get("selection") or {}).get("date_quota"),
        },
    )

    grid_report = audit_grid(
        grid_path,
        training_registry_path,
        manifest_path,
        grid_summary_path,
        100,
        ("train", "validation"),
        DEFAULT_DATES,
        20260822,
        DEFAULT_MODELS,
        DEFAULT_MODELS,
        "baseline_v1",
        72,
    )
    record(
        "formal_grid_strict_complete",
        grid_report["strict_complete"],
        {
            "expected": grid_report["expected"],
            "observed": grid_report["observed"],
            "jsonl_audit": grid_report["jsonl_audit"],
            "row_failures": grid_report["row_failures"],
            "panel_audit": grid_report["panel_audit"],
            "summary_audit": grid_report["summary_audit"],
        },
    )

    fit_payload: dict[str, Any] | None = None
    if fit_exclusions_path.is_file():
        fit_payload = _read(fit_exclusions_path)
        source_grid = Path(str(fit_payload.get("source_grid") or "")).expanduser().resolve()
        fit_seeds = validate_fit_exclusions(fit_payload, source_grid)
        record(
            "router_fit_200_sources_frozen",
            len(fit_seeds) == 200
            and fit_payload.get("collection_fingerprint")
            == grid_report["expected"]["collection_fingerprint"]
            and fit_payload.get("registry_and_code_sha256") == training_registry_hash,
            {
                "file_sha256": _sha256(fit_exclusions_path),
                "records_sha256": fit_payload.get("records_sha256"),
                "records": len(fit_seeds),
            },
        )
    else:
        record("router_fit_200_sources_frozen", False, "artifact_not_created")

    training_report: dict[str, Any] | None = None
    if training_report_path.is_file() and weights_path.is_file():
        training_report = _read(training_report_path)
        try:
            best_fixed = _validate_training_report(training_report, DEFAULT_EXPERTS)
            _validate_weights(weights_path, DEFAULT_EXPERTS)
            training_ok = (
                training_report.get("weights_sha256") == _sha256(weights_path)
                and training_report.get("registry_and_code_sha256")
                == training_registry_hash
                and Path(str(training_report.get("weights") or "")).expanduser().resolve()
                == weights_path.expanduser().resolve()
            )
            detail = {
                "best_fixed": best_fixed,
                "training_report_sha256": _sha256(training_report_path),
                "weights_sha256": _sha256(weights_path),
            }
        except Exception as exc:  # audit report, not a serving fallback
            training_ok = False
            detail = f"{type(exc).__name__}: {exc}"
        record("learned_router_training_frozen", training_ok, detail)
    else:
        record(
            "learned_router_training_frozen",
            False,
            {
                "training_report_exists": training_report_path.is_file(),
                "weights_exists": weights_path.is_file(),
            },
        )

    final_registry = None
    if final_registry_path.is_file():
        final_registry = load_registry(final_registry_path)
        raw = final_registry.raw
        protocol = raw.get("test_protocol") or {}
        manifest_seal = raw.get("source_manifest_seal") or {}
        fit_protocol = raw.get("router_fit_source_exclusions") or {}
        fixed_specs_exact = all(
            final_registry.require(model_id)
            == _rebase_spec(
                fixed.require(model_id), fixed.path.parent, final_registry.path.parent
            )
            for model_id in FIXED_MODEL_IDS
        )
        router_specs_ok = all(
            _logical_router_spec(final_registry.require(model_id)).get("experts")
            == list(DEFAULT_EXPERTS)
            and _logical_router_spec(final_registry.require(model_id)).get("switch_step")
            == 72
            for model_id in ("rule_router", "learned_router")
        )
        final_ok = (
            raw.get("schema") == FINAL_REGISTRY_SCHEMA
            and tuple(final_registry.models) == FINAL_MODEL_IDS
            and raw.get("sealed_before_test") is True
            and raw.get("test_used_for_fit") is False
            and raw.get("pre_selection_test_access") is False
            and raw.get("fixed_registry_sha256") == fixed_hash
            and fixed_specs_exact
            and router_specs_ok
            and protocol.get("model_ids") == list(FINAL_MODEL_IDS)
            and manifest_seal.get("file_sha256") == _sha256(manifest_path)
            and manifest_seal.get("records") == 2090
            and manifest_seal.get("unique_seeds") == 2090
            and manifest_seal.get("dates")
            == ["2026-08-18", "2026-08-19", "2026-08-20"]
            and manifest_seal.get("split_counts")
            == {"test": 210, "train": 1670, "validation": 210}
            and protocol.get("frozen_panel_file_sha256") == _sha256(test_panel_path)
            and protocol.get("quarantine_file_sha256") == _sha256(quarantine_path)
            and protocol.get("expected_games") == 18200
            and fit_payload is not None
            and fit_protocol.get("file_sha256") == _sha256(fit_exclusions_path)
            and fit_protocol.get("records_sha256") == fit_payload.get("records_sha256")
        )
        if training_report is not None:
            final_ok = final_ok and (
                raw.get("training_report_sha256") == _sha256(training_report_path)
                and raw.get("learned_weights_sha256") == _sha256(weights_path)
            )
        record(
            "final_registry_exact_14_and_sealed",
            final_ok,
            {
                "schema": raw.get("schema"),
                "models": list(final_registry.models),
                "registry_and_code_sha256": registry_fingerprint(final_registry),
            },
        )
    else:
        record("final_registry_exact_14_and_sealed", False, "artifact_not_created")

    if fast_registry_path.is_file() and final_registry is not None:
        fast = load_registry(fast_registry_path)
        preserved_keys = (
            "sealed_before_test",
            "test_used_for_fit",
            "pre_selection_test_access",
            "fixed_registry_sha256",
            "training_report_sha256",
            "training_report_schema",
            "training_implementation_sha256",
            "learned_weights_sha256",
            "best_fixed_model",
            "router_experts",
            "source_manifest_seal",
            "fit_protocol",
            "router_fit_source_exclusions",
            "test_protocol",
        )
        proxy_specs_ok = all(
            _logical_router_spec(fast.require(model_id))
            == final_registry.require(model_id)
            for model_id in ("rule_router", "learned_router")
        )
        fast_ok = (
            tuple(fast.models) == FINAL_MODEL_IDS
            and all(fast.raw.get(key) == final_registry.raw.get(key) for key in preserved_keys)
            and proxy_specs_ok
            and fast.raw.get("source_registry_raw_sha256")
            == hashlib.sha256(
                json.dumps(
                    final_registry.raw,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        )
        record(
            "fast_registry_preserves_full_seal",
            fast_ok,
            {
                "models": list(fast.models),
                "converted_routers": fast.raw.get("converted_routers"),
            },
        )
    else:
        record(
            "fast_registry_preserves_full_seal",
            False,
            {
                "final_registry_exists": final_registry_path.is_file(),
                "fast_registry_exists": fast_registry_path.is_file(),
            },
        )

    return {
        "schema": SCHEMA,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "environment_games_started": False,
        "final_test_results_opened": False,
        "checks": checks,
        "evidence": evidence,
        "blockers": blockers,
        "ready_for_one_time_final_test": not blockers,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=Path, default=HERE / "router_grid_train_val.jsonl")
    parser.add_argument("--grid-summary", type=Path, default=HERE / "router_grid_train_val_summary.json")
    parser.add_argument("--fixed-registry", type=Path, default=HERE / "fixed_registry.json")
    parser.add_argument("--training-registry", type=Path, default=HERE / "router_training_registry.json")
    parser.add_argument("--manifest", type=Path, default=HERE / "evaluation_seed_manifest.jsonl")
    parser.add_argument("--quarantine", type=Path, default=HERE / "test_exposure_quarantine.json")
    parser.add_argument("--test-panel", type=Path, default=HERE / "final_test_panel.json")
    parser.add_argument("--fit-exclusions", type=Path, default=HERE / "router_fit_source_exclusions.json")
    parser.add_argument("--training-report", type=Path, default=HERE / "learned_router_training_report.json")
    parser.add_argument("--weights", type=Path, default=HERE / "learned_router_weights.npz")
    parser.add_argument("--final-registry", type=Path, default=HERE / "final_registry.json")
    parser.add_argument("--fast-registry", type=Path, default=HERE.parent / "v11_iterative_league" / "fast_registry.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-incomplete", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit_chain(
        grid_path=args.grid,
        grid_summary_path=args.grid_summary,
        fixed_registry_path=args.fixed_registry,
        training_registry_path=args.training_registry,
        manifest_path=args.manifest,
        quarantine_path=args.quarantine,
        test_panel_path=args.test_panel,
        fit_exclusions_path=args.fit_exclusions,
        training_report_path=args.training_report,
        weights_path=args.weights,
        final_registry_path=args.final_registry,
        fast_registry_path=args.fast_registry,
    )
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "ready_for_one_time_final_test": report[
                    "ready_for_one_time_final_test"
                ],
                "passed": sum(report["checks"].values()),
                "checks": len(report["checks"]),
                "blockers": report["blockers"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["ready_for_one_time_final_test"] or args.allow_incomplete else 2


if __name__ == "__main__":
    raise SystemExit(main())
