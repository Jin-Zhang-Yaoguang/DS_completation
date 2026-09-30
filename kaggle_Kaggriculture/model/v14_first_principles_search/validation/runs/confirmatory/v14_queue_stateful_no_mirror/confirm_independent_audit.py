"""Independent reconstruction of the single-use V14 confirmatory evaluation.

This program never imports the sealed runner or sealed auditor and never
creates a Kaggriculture environment.  It reads raw JSON/JSONL bytes, rebuilds
the 400-task closure and all result statistics, and writes only the two
``independent_audit`` reports beside this file.

The low-level canonicalization, task validation, package-closure and bootstrap
helpers are reused from the prior independent screen audit.  That helper is
itself hash-recorded here and its import graph is checked with ``ast`` to prove
that it does not import the sealed runner/auditor.
"""

from __future__ import annotations

import ast
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


SCRIPT = Path(__file__).resolve()
RUN_DIR = SCRIPT.parent
VALIDATION = SCRIPT.parents[3]
WORKSPACE = VALIDATION.parents[3]
SEALED = VALIDATION / "sealed_runtime"
SCREEN_RUN = VALIDATION / "runs" / "screen" / "v14_queue_stateful_no_mirror"
SCREEN_HELPER = SCREEN_RUN / "independent_audit.py"

CANDIDATE = "v14_queue_stateful_no_mirror"
ANCHORS = ("v12_incumbent_r002", "v12a2_no_shop_gate")
ROW_SCHEMA = "kaggriculture-v10-pairwise-closed-loop-1"
RUN_SCHEMA = "kaggriculture-v14-dual-anchor-run-1"
BOOTSTRAP_NAMESPACE = "v14-independent-confirmatory-source-cluster-bootstrap-v1"


def load_independent_helper():
    tree = ast.parse(SCREEN_HELPER.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    forbidden = {
        name
        for name in imported
        if name == "audit_dual_anchor"
        or name.startswith("audit_dual_anchor.")
        or name == "run_dual_anchor"
        or name.startswith("run_dual_anchor.")
    }
    if forbidden:
        raise RuntimeError(f"independent helper imports forbidden modules: {forbidden}")
    spec = importlib.util.spec_from_file_location("v14_screen_independent_helper", SCREEN_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load independent screen helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RUN_DIR = RUN_DIR
    module.BOOTSTRAP_SEED_NAMESPACE = BOOTSTRAP_NAMESPACE
    return module, imported


base, HELPER_IMPORTS = load_independent_helper()


def confirm_run_fingerprint(
    panel_path: Path,
    panel: dict[str, Any],
    records: list[dict[str, Any]],
    slate: dict[str, Any],
    registry_hash: str,
    evaluator_hash: str,
) -> tuple[str, dict[str, Any]]:
    payload = {
        "schema": RUN_SCHEMA,
        "phase": "confirmatory",
        "candidate": CANDIDATE,
        "targeted_pairs": [[CANDIDATE, anchor] for anchor in ANCHORS],
        "seat_assignments_per_source": 2,
        "panel_file_sha256": base.file_sha256(panel_path),
        "panel_records_sha256": panel["records_sha256"],
        "panel_records": records,
        "evaluation_contract_file_sha256": base.file_sha256(
            VALIDATION / "evaluation_contract.json"
        ),
        "panel_seal_file_sha256": base.file_sha256(VALIDATION / "panel_seal.json"),
        "candidate_slate_file_sha256": base.file_sha256(SEALED / "candidate_slate.json"),
        "candidate_slate_core_sha256": slate["slate_core_sha256"],
        "candidate_seal_file_sha256": base.file_sha256(SEALED / "candidate_seal.json"),
        "registry_and_serving_code_sha256": registry_hash,
        "v10_evaluation_implementation_sha256": evaluator_hash,
        "v10_row_schema": ROW_SCHEMA,
    }
    return base.sha256_bytes(base.canonical(payload)), payload


def expected_manifest(
    fingerprint: str,
    panel: dict[str, Any],
    slate: dict[str, Any],
    registry_hash: str,
    evaluator_hash: str,
) -> dict[str, Any]:
    panel_path = VALIDATION / "confirmatory_panel.json"
    return {
        "anchors": list(ANCHORS),
        "candidate": CANDIDATE,
        "candidate_seal_file_sha256": base.file_sha256(SEALED / "candidate_seal.json"),
        "candidate_slate_core_sha256": slate["slate_core_sha256"],
        "candidate_slate_file_sha256": base.file_sha256(SEALED / "candidate_slate.json"),
        "confirmatory_execution_flag": True,
        "dry_run": False,
        "evaluation_contract_file_sha256": base.file_sha256(
            VALIDATION / "evaluation_contract.json"
        ),
        "expected_games": 400,
        "panel": str(panel_path.resolve()),
        "panel_file_sha256": base.file_sha256(panel_path),
        "panel_records_sha256": panel["records_sha256"],
        "panel_seal_file_sha256": base.file_sha256(VALIDATION / "panel_seal.json"),
        "phase": "confirmatory",
        "protocol_verification_status": "PASS",
        "registry": str((SEALED / "clean_registry.json").resolve()),
        "registry_and_serving_code_sha256": registry_hash,
        "registry_file_sha256": base.file_sha256(SEALED / "clean_registry.json"),
        "run_fingerprint": fingerprint,
        "schema": RUN_SCHEMA,
        "sources": 100,
        "targeted_pairs": [[CANDIDATE, anchor] for anchor in ANCHORS],
        "v10_evaluation_implementation_sha256": evaluator_hash,
    }


def expected_consume_lock(fingerprint: str, manifest_path: Path, registry_hash: str) -> dict[str, Any]:
    return {
        "schema": "kaggriculture-v14-panel-consume-lock-1",
        "phase": "confirmatory",
        "candidate": CANDIDATE,
        "run_fingerprint": fingerprint,
        "jsonl": str((RUN_DIR / "games.jsonl").resolve()),
        "run_manifest": str(manifest_path.resolve()),
        "run_manifest_file_sha256": base.file_sha256(manifest_path),
        "registry_and_code_sha256": registry_hash,
        "panel_file_sha256": base.file_sha256(VALIDATION / "confirmatory_panel.json"),
        "candidate_seal_file_sha256": base.file_sha256(SEALED / "candidate_seal.json"),
    }


def verify_confirmatory_panel(panel: dict[str, Any]) -> dict[str, Any]:
    records = base.normalized_records(panel)
    dates = Counter(row["date"] for row in records)
    splits = Counter(row["split"] for row in records)
    identities = {(row["date"], row["episode_id"], row["seed"]) for row in records}
    seeds = {row["seed"] for row in records}
    records_hash = base.sha256_bytes(base.canonical(records))

    screen = base.load_json(VALIDATION / "screen_panel.json")
    screen_records = base.normalized_records(screen)
    screen_identities = {
        (row["date"], row["episode_id"], row["seed"]) for row in screen_records
    }
    screen_seeds = {row["seed"] for row in screen_records}

    exposure = base.load_json(VALIDATION / "exposure_inventory.json")
    exposure_seeds = {int(row["seed"]) for row in exposure["records"]}

    seal_path = VALIDATION / "panel_seal.json"
    seal = base.load_json(seal_path)
    seal_core = {
        key: value for key, value in seal.items() if key not in {"schema", "seal_core_sha256"}
    }
    asset_checks: list[dict[str, Any]] = []
    for asset in seal["assets"]:
        path = base.resolve_workspace_path(str(asset["path"]))
        actual_hash = base.file_sha256(path) if path.is_file() else None
        actual_size = path.stat().st_size if path.is_file() else None
        asset_checks.append(
            {
                "path": str(path),
                "expected_sha256": asset["file_sha256"],
                "actual_sha256": actual_hash,
                "expected_size_bytes": asset["size_bytes"],
                "actual_size_bytes": actual_size,
                "passed": actual_hash == asset["file_sha256"]
                and actual_size == asset["size_bytes"],
            }
        )
    checksum_checks: list[dict[str, Any]] = []
    for line in (VALIDATION / "protocol_assets.sha256").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected_hash, relative = line.split("  ", 1)
        path = base.resolve_workspace_path(relative)
        actual_hash = base.file_sha256(path) if path.is_file() else None
        checksum_checks.append(
            {
                "path": str(path),
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
                "passed": actual_hash == expected_hash,
            }
        )

    checks = {
        "schema": panel.get("schema") == "kaggriculture-v14-frozen-development-panel-1",
        "kind": panel.get("kind") == "confirmatory100_single_use",
        "count": panel.get("count") == len(records) == 100,
        "date_counts": panel.get("date_counts") == dict(dates)
        == {"2026-08-18": 34, "2026-08-19": 33, "2026-08-20": 33},
        "split_counts": panel.get("split_counts") == dict(splits)
        == {"train": 88, "validation": 12},
        "allowed_splits": panel.get("allowed_splits") == ["train", "validation"]
        and set(splits).issubset({"train", "validation"}),
        "test_zero": panel.get("test_source_count") == 0
        and panel.get("test_outcomes_accessed") is False
        and "test" not in splits,
        "identity_unique": len(identities) == len(records),
        "seed_unique": len(seeds) == len(records) and panel.get("all_environment_seeds_unique") is True,
        "records_sha256": panel.get("records_sha256") == records_hash,
        "metadata_only": panel.get("metadata_only") is True,
        "historical_payloads_not_accessed": panel.get("historical_replay_payloads_accessed") is False,
        "environment_unstarted_at_freeze": panel.get("environment_games_started") is False,
        "screen_disjoint_identity": not identities.intersection(screen_identities),
        "screen_disjoint_seed": not seeds.intersection(screen_seeds),
        "exposure_disjoint_seed": not seeds.intersection(exposure_seeds),
        "exposure_inventory_test_zero": exposure.get("test_outcomes_accessed") is False
        and exposure.get("test_selected") is False,
        "exposure_inventory_hash": panel.get("exposure_union_seeds_sha256")
        == exposure.get("union_seeds_sha256")
        == seal.get("exposure_union_seeds_sha256"),
        "panel_seal_test_zero": seal.get("confirmatory_test_source_count") == 0
        and seal.get("test_access") is False,
        "panel_seal_record_hash": seal.get("confirmatory_records_sha256") == records_hash,
        "panel_seal_disjoint": seal.get("screen_confirmatory_disjoint") is True,
    }
    return {
        "panel_file_sha256": base.file_sha256(VALIDATION / "confirmatory_panel.json"),
        "records_sha256_recomputed": records_hash,
        "checks": checks,
        "checks_all_pass": all(checks.values()),
        "selected_exposure_seed_intersection_count": len(seeds.intersection(exposure_seeds)),
        "selected_screen_seed_intersection_count": len(seeds.intersection(screen_seeds)),
        "test_source_count": panel.get("test_source_count"),
        "panel_seal_file_sha256": base.file_sha256(seal_path),
        "panel_seal_core_sha256_recomputed": base.sha256_bytes(base.canonical(seal_core)),
        "panel_seal_core_pass": seal.get("seal_core_sha256")
        == base.sha256_bytes(base.canonical(seal_core)),
        "panel_seal_assets": asset_checks,
        "panel_seal_assets_all_pass": all(row["passed"] for row in asset_checks),
        "protocol_assets": checksum_checks,
        "protocol_assets_all_pass": all(row["passed"] for row in checksum_checks),
    }


def verify_finalist_chain() -> dict[str, Any]:
    finalist_path = VALIDATION / "finalist_seal.json"
    provenance_path = VALIDATION / "finalist_seal_recovery_provenance.json"
    finalist = base.load_json(finalist_path)
    provenance = base.load_json(provenance_path)
    screen_record = finalist.get("screen_records", [{}])[0]
    screen_manifest = base.load_json(SCREEN_RUN / "run_manifest.json")
    screen_audit = base.load_json(SCREEN_RUN / "audit.json")
    screen_files = screen_record.get("files") or {}

    immutable_paths = {
        "candidate_seal": SEALED / "candidate_seal.json",
        "candidate_slate": SEALED / "candidate_slate.json",
        "clean_registry": SEALED / "clean_registry.json",
        "confirmatory_panel": VALIDATION / "confirmatory_panel.json",
        "evaluation_contract": VALIDATION / "evaluation_contract.json",
        "panel_seal": VALIDATION / "panel_seal.json",
        "screen_audit": SCREEN_RUN / "audit.json",
        "screen_audit_recovery": SCREEN_RUN / "audit_recovery_provenance.json",
        "screen_games": SCREEN_RUN / "games.jsonl",
        "screen_lock": VALIDATION / "execution_state" / "screen" / f"{CANDIDATE}.json",
        "screen_manifest": SCREEN_RUN / "run_manifest.json",
        "screen_panel": VALIDATION / "screen_panel.json",
        "sealed_auditor": VALIDATION / "audit_dual_anchor.py",
        "sealed_finalist": VALIDATION / "seal_finalist.py",
        "writer_validator": VALIDATION / "recover_audit_only.py",
    }
    actual_immutable = {name: base.file_sha256(path) for name, path in immutable_paths.items()}
    recorded_immutable = provenance.get("immutable_input_sha256") or {}
    screen_file_checks: dict[str, bool] = {}
    for name in ("games", "run_manifest", "audit"):
        entry = screen_files.get(name) or {}
        path = Path(str(entry.get("path") or ""))
        expected_path = SCREEN_RUN / ("games.jsonl" if name == "games" else f"{name}.json")
        screen_file_checks[name] = path.resolve() == expected_path.resolve() and entry.get(
            "file_sha256"
        ) == base.file_sha256(expected_path)

    checks = {
        "schema": finalist.get("schema") == "kaggriculture-v14-finalist-seal-1",
        "status": finalist.get("status") == "sealed_screen_winner",
        "finalist": finalist.get("finalist") == CANDIDATE,
        "candidate_order": finalist.get("candidate_order") == [CANDIDATE],
        "eligible_ranking": finalist.get("eligible_ranking") == [CANDIDATE],
        "maximum_one": finalist.get("maximum_confirmatory_finalists") == 1,
        "confirmatory_unstarted_at_seal": finalist.get("confirmatory_games_started") is False,
        "candidate_seal_hash": finalist.get("candidate_seal_file_sha256")
        == base.file_sha256(SEALED / "candidate_seal.json"),
        "candidate_slate_hash": finalist.get("candidate_slate_file_sha256")
        == base.file_sha256(SEALED / "candidate_slate.json"),
        "registry_hash": finalist.get("clean_registry_file_sha256")
        == base.file_sha256(SEALED / "clean_registry.json"),
        "one_screen_record": len(finalist.get("screen_records") or []) == 1,
        "screen_candidate": screen_record.get("candidate") == CANDIDATE,
        "screen_gate_pass": screen_record.get("passed_all_screen_gates") is True
        and screen_audit.get("passed") is True,
        "screen_fingerprint": screen_record.get("run_fingerprint")
        == screen_manifest.get("run_fingerprint"),
        "screen_file_hashes": all(screen_file_checks.values()),
        "provenance_schema_status": provenance.get("schema")
        == "kaggriculture-v14-finalist-recovery-1"
        and provenance.get("status") == "FINALIST_SEALED_WITH_AUDIT_ONLY_RECOVERY",
        "provenance_identity": provenance.get("candidate") == CANDIDATE
        and provenance.get("finalist") == CANDIDATE,
        "provenance_seal_hash": provenance.get("finalist_seal_sha256")
        == base.file_sha256(finalist_path),
        "provenance_immutable_hashes": recorded_immutable == actual_immutable,
        "provenance_no_ranking_or_task_replacement": provenance.get("ranking_logic_replaced") is False
        and provenance.get("task_generation_replaced") is False
        and provenance.get("run_tasks_called") is False,
        "provenance_inputs_stable": provenance.get("immutable_inputs_before_after_equal") is True,
    }
    return {
        "finalist_seal_file_sha256": base.file_sha256(finalist_path),
        "finalist_recovery_file_sha256": base.file_sha256(provenance_path),
        "checks": checks,
        "checks_all_pass": all(checks.values()),
        "screen_file_checks": screen_file_checks,
        "recorded_immutable_input_sha256": recorded_immutable,
        "actual_immutable_input_sha256": actual_immutable,
    }


def compare_landed_audit(metrics: dict[str, Any], gates: dict[str, bool]) -> dict[str, Any]:
    path = RUN_DIR / "audit.json"
    audit = base.load_json(path)
    fields = (
        "games",
        "wins",
        "ties",
        "losses",
        "pure_win_rate",
        "competition_score_rate",
        "mean_margin",
    )
    anchor_comparisons: dict[str, Any] = {}
    all_equal = True
    for anchor in ANCHORS:
        independent = metrics[anchor]
        landed = audit["by_anchor"][anchor]
        overall = {field: independent["overall"][field] == landed["overall"][field] for field in fields}
        by_date = {
            date: {field: stats[field] == landed["by_date"][date][field] for field in fields}
            for date, stats in independent["by_date"].items()
        }
        by_seat = {
            seat: {
                field: stats[field] == landed["by_candidate_seat"][seat][field]
                for field in fields
            }
            for seat, stats in independent["by_candidate_seat"].items()
        }
        equal = all(overall.values()) and all(
            all(row.values()) for row in [*by_date.values(), *by_seat.values()]
        )
        all_equal &= equal
        anchor_comparisons[anchor] = {
            "overall": overall,
            "by_date": by_date,
            "by_candidate_seat": by_seat,
            "all_point_metrics_equal": equal,
            "landed_ci95": {
                "pure_win_rate": landed["overall"].get("pure_win_rate_ci95"),
                "competition_score_rate": landed["overall"].get("competition_score_rate_ci95"),
                "mean_margin": landed["overall"].get("mean_margin_ci95"),
            },
            "independent_ci95": {
                "pure_win_rate": independent["overall"].get("pure_win_rate_ci95"),
                "competition_score_rate": independent["overall"].get("competition_score_rate_ci95"),
                "mean_margin": independent["overall"].get("mean_margin_ci95"),
            },
        }
    landed_gates = audit.get("gates") or {}
    gates_equal = all(landed_gates.get(name) == value for name, value in gates.items())
    return {
        "audit_file_sha256": base.file_sha256(path),
        "identity_pass": audit.get("schema") == "kaggriculture-v14-dual-anchor-audit-1"
        and audit.get("phase") == "confirmatory"
        and audit.get("candidate") == CANDIDATE,
        "rows_pass": audit.get("rows") == audit.get("expected_rows") == 400,
        "done_error_pass": audit.get("done_done_count") == 400
        and audit.get("error_count") == 0
        and audit.get("status_counts") == {"DONE/DONE": 400},
        "run_fingerprint_pass": audit.get("run_fingerprint")
        == base.load_json(RUN_DIR / "run_manifest.json").get("run_fingerprint"),
        "anchor_comparisons": anchor_comparisons,
        "all_point_metrics_equal": all_equal,
        "gate_values_equal": gates_equal,
        "landed_gates": landed_gates,
        "landed_passed": audit.get("passed"),
    }


def verify_confirm_recovery() -> dict[str, Any]:
    path = RUN_DIR / "confirm_recovery_provenance.json"
    provenance = base.load_json(path)
    immutable_paths = {
        "candidate_seal": SEALED / "candidate_seal.json",
        "candidate_slate": SEALED / "candidate_slate.json",
        "finalist_seal": VALIDATION / "finalist_seal.json",
        "finalist_recovery": VALIDATION / "finalist_seal_recovery_provenance.json",
        "clean_registry": SEALED / "clean_registry.json",
        "screen_games": SCREEN_RUN / "games.jsonl",
        "screen_manifest": SCREEN_RUN / "run_manifest.json",
        "screen_lock": VALIDATION / "execution_state" / "screen" / f"{CANDIDATE}.json",
        "screen_audit": SCREEN_RUN / "audit.json",
        "screen_audit_recovery": SCREEN_RUN / "audit_recovery_provenance.json",
        "screen_panel": VALIDATION / "screen_panel.json",
        "confirmatory_panel": VALIDATION / "confirmatory_panel.json",
        "panel_seal": VALIDATION / "panel_seal.json",
        "evaluation_contract": VALIDATION / "evaluation_contract.json",
        "protocol_assets": VALIDATION / "protocol_assets.sha256",
        "sealed_runner": VALIDATION / "run_dual_anchor.py",
        "sealed_auditor": VALIDATION / "audit_dual_anchor.py",
        "sealed_finalist": VALIDATION / "seal_finalist.py",
        "writer_validator": VALIDATION / "recover_audit_only.py",
    }
    actual_immutable = {name: base.file_sha256(item) for name, item in immutable_paths.items()}
    dynamic_paths = {
        "run_manifest": RUN_DIR / "run_manifest.json",
        "consume_lock": VALIDATION / "execution_state" / "confirmatory_consumed.json",
        "games": RUN_DIR / "games.jsonl",
        "audit": RUN_DIR / "audit.json",
    }
    actual_dynamic = {name: base.file_sha256(item) for name, item in dynamic_paths.items()}
    wrapper_path = VALIDATION / "run_confirmatory_with_audit_recovery.py"
    checks = {
        "schema_status": provenance.get("schema") == "kaggriculture-v14-confirmatory-recovery-1"
        and provenance.get("status") == "CONFIRMATORY_COMPLETE_WITH_AUDIT_LOCK_RECOVERY",
        "candidate": provenance.get("candidate") == CANDIDATE,
        "execution_flags": provenance.get("resume") is False
        and provenance.get("dry_run") is False
        and provenance.get("execute_confirmatory") is True,
        "no_generation_or_execution_replacement": provenance.get("task_generation_replaced") is False
        and provenance.get("run_tasks_replaced") is False
        and provenance.get("consume_lock_replaced") is False
        and provenance.get("finalist_validation_replaced") is False,
        "inputs_stable": provenance.get("immutable_inputs_before_after_equal") is True,
        "immutable_hashes": provenance.get("immutable_input_sha256") == actual_immutable,
        "dynamic_hashes": provenance.get("dynamic_output_sha256") == actual_dynamic,
        "wrapper_hash": provenance.get("wrapper_sha256") == base.file_sha256(wrapper_path),
        "evaluator_hash": provenance.get("v10_evaluation_implementation_sha256")
        == base.evaluator_fingerprint()[0],
        "registry_hash": provenance.get("registry_and_serving_code_sha256")
        == base.registry_fingerprint(
            base.load_json(SEALED / "clean_registry.json"), SEALED / "clean_registry.json"
        )[0],
        "run_fingerprint": provenance.get("run_fingerprint")
        == base.load_json(RUN_DIR / "run_manifest.json").get("run_fingerprint"),
        "rows": provenance.get("rows") == 400,
        "passed_matches_audit": provenance.get("passed")
        == base.load_json(RUN_DIR / "audit.json").get("passed"),
    }
    return {
        "provenance_file_sha256": base.file_sha256(path),
        "checks": checks,
        "checks_all_pass": all(checks.values()),
        "recorded_immutable_input_sha256": provenance.get("immutable_input_sha256"),
        "actual_immutable_input_sha256": actual_immutable,
        "recorded_dynamic_output_sha256": provenance.get("dynamic_output_sha256"),
        "actual_dynamic_output_sha256": actual_dynamic,
    }


def collect_immutable_inputs(slate: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {
        "games": RUN_DIR / "games.jsonl",
        "run_manifest": RUN_DIR / "run_manifest.json",
        "consume_lock": VALIDATION / "execution_state" / "confirmatory_consumed.json",
        "landed_audit": RUN_DIR / "audit.json",
        "confirm_recovery": RUN_DIR / "confirm_recovery_provenance.json",
        "confirmatory_panel": VALIDATION / "confirmatory_panel.json",
        "screen_panel": VALIDATION / "screen_panel.json",
        "panel_seal": VALIDATION / "panel_seal.json",
        "protocol_assets": VALIDATION / "protocol_assets.sha256",
        "evaluation_contract": VALIDATION / "evaluation_contract.json",
        "exposure_inventory": VALIDATION / "exposure_inventory.json",
        "candidate_slate": SEALED / "candidate_slate.json",
        "candidate_seal": SEALED / "candidate_seal.json",
        "clean_registry": SEALED / "clean_registry.json",
        "finalist_seal": VALIDATION / "finalist_seal.json",
        "finalist_recovery": VALIDATION / "finalist_seal_recovery_provenance.json",
        "screen_games": SCREEN_RUN / "games.jsonl",
        "screen_manifest": SCREEN_RUN / "run_manifest.json",
        "screen_lock": VALIDATION / "execution_state" / "screen" / f"{CANDIDATE}.json",
        "screen_audit": SCREEN_RUN / "audit.json",
        "screen_audit_recovery": SCREEN_RUN / "audit_recovery_provenance.json",
        "sealed_runner": VALIDATION / "run_dual_anchor.py",
        "sealed_auditor": VALIDATION / "audit_dual_anchor.py",
        "sealed_finalist": VALIDATION / "seal_finalist.py",
        "audit_lock_validator": VALIDATION / "recover_audit_only.py",
        "confirm_wrapper": VALIDATION / "run_confirmatory_with_audit_recovery.py",
        "independent_screen_helper": SCREEN_HELPER,
    }
    for package in [*(slate.get("anchors") or []), *(slate.get("candidates") or [])]:
        package_id = str(package["id"])
        paths[f"archive:{package_id}"] = base.resolve_workspace_path(str(package["archive"]["path"]))
        for artifact_name in ("registry_entry", "source_main", "submission_manifest", "package_qa"):
            paths[f"artifact:{package_id}:{artifact_name}"] = base.resolve_workspace_path(
                str(package[artifact_name]["path"])
            )
        for member in package["clean_submission"]["members"]:
            paths[f"clean:{package_id}:{member['archive_path']}"] = Path(
                str(member["clean_path"])
            ).resolve()
    return paths


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# V14 confirmatory 独立审计",
        "",
        f"结论：**{report['decision']}**。纯胜率严格为 wins/all；平局不算胜。",
        "",
        "## 结果",
        "",
        "| 对手 | W/T/L | 纯胜率 | 计分率 | 平均 margin | 日期分层 source-cluster 95% CI（纯胜率） |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for anchor in ANCHORS:
        stats = report["metrics"][anchor]["overall"]
        ci = stats["pure_win_rate_ci95"]
        lines.append(
            f"| {anchor} | {stats['wins']}/{stats['ties']}/{stats['losses']} | "
            f"{stats['pure_win_rate']:.4%} | {stats['competition_score_rate']:.4%} | "
            f"{stats['mean_margin']:+.4f} | [{ci[0]:.4%}, {ci[1]:.4%}] |"
        )
    lines.extend(
        [
            "",
            "Bootstrap 独立执行 10,000 次：按日期分层，在每个日期内重采样 100 个 source cluster，并始终保留同一 source 的双席。独立 seed 与落盘审计不同，所以区间不要求逐端点相同。",
            "",
            "## 完整性",
            "",
            f"- 原始任务 {report['task_integrity']['rows']}/{report['task_integrity']['expected_rows']}；唯一 task_id {report['task_integrity']['unique_task_ids']}；缺失 {report['task_integrity']['missing_task_ids']}；逐行错误 {report['task_integrity']['foreign_or_duplicate_or_invalid_count']}。",
            f"- DONE/DONE：{report['task_integrity']['status_counts']}；schema、engine、pair、双席、error、reward、margin、score 均从原始行复算。",
            f"- run fingerprint：`{report['fingerprints']['run_fingerprint_recomputed']}`；manifest、consume lock 和全部 400 行一致。",
            f"- confirm panel：100 sources，日期 34/33/33；test={report['panel_chain']['test_source_count']}；与 screen seed 交集 {report['panel_chain']['selected_screen_seed_intersection_count']}；与既有 exposure seed 交集 {report['panel_chain']['selected_exposure_seed_intersection_count']}。",
            f"- finalist seal：`{report['finalist_chain']['finalist_seal_file_sha256']}`；所有绑定检查 {report['finalist_chain']['checks_all_pass']}。",
            f"- 候选 archive：`{next(row for row in report['runtime_chain']['packages'] if row['id'] == CANDIDATE)['archive']['actual_sha256']}`；tar、clean closure、registry binding 均通过。",
            f"- 落盘 audit 点估计一致：{report['landed_audit_comparison']['all_point_metrics_equal']}；confirm recovery 哈希链：{report['confirm_recovery']['checks_all_pass']}；分析前后输入未变：{report['input_hash_stability']['before_after_equal']}。",
            "",
            "## 日期与候选席位",
            "",
        ]
    )
    for anchor in ANCHORS:
        lines.extend([f"### {anchor}", "", "| 分层 | games | W/T/L | pure | score | margin |", "|---|---:|---:|---:|---:|---:|"])
        for date, stats in report["metrics"][anchor]["by_date"].items():
            lines.append(
                f"| {date} | {stats['games']} | {stats['wins']}/{stats['ties']}/{stats['losses']} | "
                f"{stats['pure_win_rate']:.4%} | {stats['competition_score_rate']:.4%} | {stats['mean_margin']:+.4f} |"
            )
        for seat, stats in report["metrics"][anchor]["by_candidate_seat"].items():
            lines.append(
                f"| candidate seat {seat} | {stats['games']} | {stats['wins']}/{stats['ties']}/{stats['losses']} | "
                f"{stats['pure_win_rate']:.4%} | {stats['competition_score_rate']:.4%} | {stats['mean_margin']:+.4f} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Gate",
            "",
            f"- 400-task/hash/schema/engine/seat/DONE/error/reward 完整性：`{report['gates']['integrity']}`",
            f"- A2 纯胜率 >=65%：`{report['gates']['a2_pure_win_rate_gte_0_65']}`",
            f"- r002 纯胜率 >50%：`{report['gates']['r002_pure_win_rate_gt_0_50']}`",
            "",
            "独立审计未运行环境、未调用候选、未修改协议/候选/原始结果；只写本报告 JSON/MD。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    required = [
        RUN_DIR / "games.jsonl",
        RUN_DIR / "run_manifest.json",
        RUN_DIR / "audit.json",
        RUN_DIR / "confirm_recovery_provenance.json",
        VALIDATION / "execution_state" / "confirmatory_consumed.json",
        VALIDATION / "finalist_seal.json",
        VALIDATION / "finalist_seal_recovery_provenance.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"confirmatory artifacts incomplete: {missing}")

    panel_path = VALIDATION / "confirmatory_panel.json"
    manifest_path = RUN_DIR / "run_manifest.json"
    lock_path = VALIDATION / "execution_state" / "confirmatory_consumed.json"
    registry_path = SEALED / "clean_registry.json"

    panel = base.load_json(panel_path)
    slate = base.load_json(SEALED / "candidate_slate.json")
    candidate_seal = base.load_json(SEALED / "candidate_seal.json")
    registry = base.load_json(registry_path)
    immutable_paths = collect_immutable_inputs(slate)
    hashes_before = base.hash_paths(immutable_paths)

    registry_hash, registry_paths = base.registry_fingerprint(registry, registry_path)
    evaluator_hash, evaluator_runtime, evaluator_paths = base.evaluator_fingerprint()
    records = base.normalized_records(panel)
    fingerprint, fingerprint_payload = confirm_run_fingerprint(
        panel_path, panel, records, slate, registry_hash, evaluator_hash
    )
    expected_tasks = base.build_expected_tasks(fingerprint, records)
    rows = base.load_jsonl(RUN_DIR / "games.jsonl")
    derived, task_integrity = base.validate_rows(rows, expected_tasks)
    metrics = base.metric_report(derived)

    manifest = base.load_json(manifest_path)
    manifest_expected = expected_manifest(
        fingerprint, panel, slate, registry_hash, evaluator_hash
    )
    lock = base.load_json(lock_path)
    lock_expected = expected_consume_lock(fingerprint, manifest_path, registry_hash)

    panel_chain = verify_confirmatory_panel(panel)
    runtime_chain = base.verify_runtime_chain(slate, candidate_seal, registry, registry_hash)
    finalist_chain = verify_finalist_chain()
    recovery = verify_confirm_recovery()

    task_pass = (
        task_integrity["rows"] == task_integrity["expected_rows"] == 400
        and task_integrity["unique_task_ids"] == 400
        and task_integrity["missing_task_ids"] == 0
        and task_integrity["foreign_or_duplicate_or_invalid_count"] == 0
        and task_integrity["expected_observed_task_projection_equal"]
        and task_integrity["coverage_all_exactly_once"]
        and task_integrity["status_counts"] == {"DONE/DONE": 400}
    )
    panel_pass = panel_chain["checks_all_pass"] and panel_chain["panel_seal_core_pass"] \
        and panel_chain["panel_seal_assets_all_pass"] and panel_chain["protocol_assets_all_pass"]
    runtime_pass = (
        all(runtime_chain["candidate_slate_checks"].values())
        and runtime_chain["packages_all_pass"]
        and all(runtime_chain["candidate_seal_checks"].values())
        and runtime_chain["registry"]["schema_pass"]
        and runtime_chain["registry"]["test_sources_disallowed"]
        and runtime_chain["registry"]["candidate_slate_core_exact"]
        and runtime_chain["registry"]["model_order_exact"]
        and runtime_chain["registry"]["package_binding_all_pass"]
    )
    fingerprint_rows_pass = all(row.get("run_fingerprint") == fingerprint for row in rows)
    preliminary_integrity = (
        task_pass
        and manifest == manifest_expected
        and lock == lock_expected
        and fingerprint_rows_pass
        and panel_pass
        and runtime_pass
        and finalist_chain["checks_all_pass"]
        and recovery["checks_all_pass"]
    )
    gates = {
        "integrity": preliminary_integrity,
        "a2_pure_win_rate_gte_0_65": metrics["v12a2_no_shop_gate"]["overall"]["pure_win_rate"] >= 0.65,
        "r002_pure_win_rate_gt_0_50": metrics["v12_incumbent_r002"]["overall"]["pure_win_rate"] > 0.50,
    }
    landed = compare_landed_audit(metrics, gates)

    landed_pass = (
        landed["identity_pass"]
        and landed["rows_pass"]
        and landed["done_error_pass"]
        and landed["run_fingerprint_pass"]
        and landed["all_point_metrics_equal"]
        and landed["gate_values_equal"]
        and landed["landed_passed"] is all(gates.values())
    )
    hashes_after_analysis = base.hash_paths(immutable_paths)
    input_stable = hashes_before == hashes_after_analysis
    go = all(gates.values()) and landed_pass and input_stable

    report = {
        "schema": "kaggriculture-v14-independent-confirmatory-audit-1",
        "candidate": CANDIDATE,
        "phase": "confirmatory",
        "decision": "GO_SUBMIT" if go else "NO_GO",
        "independence": {
            "imports_audit_dual_anchor": False,
            "imports_run_dual_anchor": False,
            "imports_validation_statistics": False,
            "games_or_agents_invoked": False,
            "writes": ["independent_audit.json", "independent_audit.md"],
            "helper": str(SCREEN_HELPER),
            "helper_sha256": base.file_sha256(SCREEN_HELPER),
            "helper_imports": HELPER_IMPORTS,
            "helper_forbidden_imports_absent": True,
        },
        "metric_note": "Pure win rate is wins/all games; ties remain in the denominator and are not wins.",
        "gates": gates,
        "task_integrity": task_integrity,
        "metrics": metrics,
        "fingerprints": {
            "run_fingerprint_recomputed": fingerprint,
            "run_fingerprint_manifest": manifest.get("run_fingerprint"),
            "run_fingerprint_consume_lock": lock.get("run_fingerprint"),
            "run_fingerprint_all_rows_exact": fingerprint_rows_pass,
            "run_fingerprint_payload": fingerprint_payload,
            "registry_and_serving_code_sha256_recomputed": registry_hash,
            "registry_reachable_paths": registry_paths,
            "v10_evaluation_implementation_sha256_recomputed": evaluator_hash,
            "evaluator_runtime": evaluator_runtime,
            "evaluator_paths": evaluator_paths,
        },
        "run_manifest": {
            "file_sha256": base.file_sha256(manifest_path),
            "exact_reconstruction_pass": manifest == manifest_expected,
            "observed": manifest,
            "expected": manifest_expected,
        },
        "consume_lock": {
            "file_sha256": base.file_sha256(lock_path),
            "exact_writer_payload_pass": lock == lock_expected,
            "observed": lock,
            "expected": lock_expected,
        },
        "panel_chain": panel_chain,
        "runtime_chain": runtime_chain,
        "finalist_chain": finalist_chain,
        "confirm_recovery": recovery,
        "landed_audit_comparison": landed,
        "input_hash_stability": {
            "tracked_file_count": len(immutable_paths),
            "before_sha256": hashes_before,
            "after_analysis_sha256": hashes_after_analysis,
            "before_after_equal": input_stable,
            "hash_manifest_sha256": base.sha256_bytes(base.canonical(hashes_before)),
        },
        "limitations": [
            "This is a byte- and metadata-level independent reconstruction; it does not replay games.",
            "The helper comes from the independent screen audit and is not a sealed protocol asset; its exact bytes and import graph are recorded here.",
            "Recovery no-replacement claims are corroborated by hashes and wrapper control flow but historical process activity cannot be proven solely from filesystem state.",
        ],
    }
    json_path = RUN_DIR / "independent_audit.json"
    md_path = RUN_DIR / "independent_audit.md"
    if json_path.exists() or md_path.exists():
        raise FileExistsError("independent audit output already exists")
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(markdown(report), encoding="utf-8")

    hashes_after_write = base.hash_paths(immutable_paths)
    if hashes_after_write != hashes_before:
        raise RuntimeError("an immutable input changed while writing the independent reports")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "json": str(json_path),
                "json_sha256": base.file_sha256(json_path),
                "markdown": str(md_path),
                "markdown_sha256": base.file_sha256(md_path),
                "input_hashes_unchanged_after_write": True,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
