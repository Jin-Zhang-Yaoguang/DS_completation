#!/usr/bin/env python3
"""Collect V14 evidence without consuming any new game panel or test outcome.

This module is intentionally read-only.  It reads a fixed set of exposed
development/oracle/QA artifacts, plus already-produced V14 validation audits and
Kaggle submission receipts when those files exist.  It never invokes an
evaluator, opens the official daily replay payloads, or queries Kaggle.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPORTING_DIR = Path(__file__).resolve().parent
V14_DIR = REPORTING_DIR.parent
MODEL_DIR = V14_DIR.parent
REPO_ROOT = MODEL_DIR.parents[1]
VALIDATION_DIR = V14_DIR / "validation"

A2 = "v12a2_no_shop_gate"
R002 = "v12_incumbent_r002"
ALLOWED_SPLITS = {"train", "validation"}
PURE_WIN_GATE_A2 = 0.65
PURE_WIN_GATE_R002 = 0.50


class EvidenceError(RuntimeError):
    """Raised when an evidence artifact violates the reporting boundary."""


def _repo_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise EvidenceError(f"evidence path escapes repository: {resolved}") from exc


def _resolve_artifact_path(value: str | Path, *, base: Path | None = None) -> Path:
    path = Path(value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        candidate_base = base or REPO_ROOT
        resolved = (candidate_base / path).resolve()
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise EvidenceError(f"artifact path is outside repository: {resolved}") from exc
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise EvidenceError(f"{_repo_path(path)}:{line_number} is not an object")
            rows.append(row)
    return rows


def _assert_no_test_flags(payload: Any, *, source: Path) -> None:
    """Reject any positive flag indicating test or fresh-outcome access.

    False-valued declarations such as ``test_consumed: false`` are retained as
    useful boundary evidence.  File names containing ``test`` are never scanned
    automatically by this module.
    """

    positive_test_keys: list[str] = []

    def visit(value: Any, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                current = f"{prefix}.{key_text}" if prefix else key_text
                normalized = key_text.lower()
                access_flags = {
                    "test_access",
                    "test_consumed",
                    "test_read",
                    "test_outcomes_accessed",
                    "test_outcomes_read",
                    "test_source_accessed",
                    "new_panel_or_test_used",
                }
                if normalized in access_flags and isinstance(item, bool) and item:
                    positive_test_keys.append(current)
                visit(item, current)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{prefix}[{index}]")

    visit(payload)
    if positive_test_keys:
        raise EvidenceError(
            f"forbidden positive test-access flags in {_repo_path(source)}: "
            + ", ".join(positive_test_keys)
        )


def _assert_source_splits(rows: Iterable[dict[str, Any]], *, source: Path) -> None:
    bad: set[str] = set()
    for row in rows:
        source_row = row.get("source")
        if not isinstance(source_row, dict):
            continue
        split = source_row.get("split")
        if split is not None and str(split) not in ALLOWED_SPLITS:
            bad.add(str(split))
    if bad:
        raise EvidenceError(
            f"forbidden source split(s) in {_repo_path(source)}: {sorted(bad)}"
        )


def _counts_from_margins(margins: Iterable[float]) -> dict[str, Any]:
    values = [float(value) for value in margins]
    games = len(values)
    if games == 0:
        raise EvidenceError("cannot summarize zero games")
    wins = sum(value > 0 for value in values)
    ties = sum(value == 0 for value in values)
    losses = games - wins - ties
    return {
        "games": games,
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "pure_win_rate": wins / games,
        "competition_score_rate": (wins + 0.5 * ties) / games,
        "mean_margin": sum(values) / games,
    }


def _check_rate_identity(metric: dict[str, Any], *, label: str) -> None:
    games = int(metric["games"])
    if games <= 0:
        raise EvidenceError(f"{label}: non-positive denominator")
    if int(metric["wins"]) + int(metric["ties"]) + int(metric["losses"]) != games:
        raise EvidenceError(f"{label}: W/T/L does not close to games")
    pure = int(metric["wins"]) / games
    score = (int(metric["wins"]) + 0.5 * int(metric["ties"])) / games
    if not math.isclose(float(metric["pure_win_rate"]), pure, abs_tol=1e-12):
        raise EvidenceError(f"{label}: pure-win denominator mismatch")
    if not math.isclose(float(metric["competition_score_rate"]), score, abs_tol=1e-12):
        raise EvidenceError(f"{label}: competition-score denominator mismatch")


def _pairwise_game_margin(row: dict[str, Any]) -> float:
    margin = row.get("margin_a")
    if not isinstance(margin, (int, float)) or isinstance(margin, bool):
        reward_a = row.get("reward_a")
        reward_b = row.get("reward_b")
        if not isinstance(reward_a, (int, float)) or not isinstance(reward_b, (int, float)):
            raise EvidenceError("pairwise row has no finite candidate margin")
        margin = float(reward_a) - float(reward_b)
    if not math.isfinite(float(margin)):
        raise EvidenceError("pairwise row has non-finite margin")
    return float(margin)


def _oracle_game_margin(row: dict[str, Any]) -> float:
    margin = row.get("margin")
    if isinstance(margin, (int, float)) and not isinstance(margin, bool):
        return float(margin)
    own = row.get("candidate_reward")
    opponent = row.get("opponent_reward")
    if not isinstance(own, (int, float)) or not isinstance(opponent, (int, float)):
        raise EvidenceError("oracle row has no finite candidate margin")
    return float(own) - float(opponent)


def _slice_metrics(
    rows: list[dict[str, Any]],
    *,
    margin_getter,
    seat_getter,
    candidate: str,
    anchor: str,
    evidence_level: str,
    evidence_id: str,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        source = row.get("source") or {}
        date = str(source.get("date") or "unknown")
        seat = str(seat_getter(row))
        margin = margin_getter(row)
        grouped[("date", date)].append(margin)
        grouped[("candidate_seat", seat)].append(margin)
    output: list[dict[str, Any]] = []
    for (dimension, slice_value), margins in sorted(grouped.items()):
        metric = _counts_from_margins(margins)
        output.append(
            {
                "evidence_id": evidence_id,
                "evidence_level": evidence_level,
                "candidate": candidate,
                "anchor": anchor,
                "dimension": dimension,
                "slice": slice_value,
                **metric,
            }
        )
    return output


def _pairwise_evidence(
    summary_path: Path,
    *,
    evidence_id: str,
    label: str,
    level: str = "dev_exposed",
    evidence_order: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[Path]]:
    summary = read_json(summary_path)
    _assert_no_test_flags(summary, source=summary_path)
    pairs = summary.get("pairs") or {}
    if len(pairs) != 1:
        raise EvidenceError(f"{_repo_path(summary_path)} must contain exactly one pair")
    pair = next(iter(pairs.values()))
    if pair.get("complete") is not True or int(pair.get("valid_games") or 0) <= 0:
        raise EvidenceError(f"{_repo_path(summary_path)} is not a complete evidence run")
    games_path = summary_path.with_name("games.jsonl")
    rows = read_jsonl(games_path)
    _assert_source_splits(rows, source=games_path)
    margins = [_pairwise_game_margin(row) for row in rows]
    metric = _counts_from_margins(margins)
    expected = {
        "games": int(pair["valid_games"]),
        "wins": int(pair["wins_a"]),
        "ties": int(pair["ties"]),
        "losses": int(pair["losses_a"]),
        "competition_score_rate": float(pair["score_rate_a"]),
        "mean_margin": float(pair["mean_margin_a"]),
    }
    for key in ("games", "wins", "ties", "losses"):
        if metric[key] != expected[key]:
            raise EvidenceError(f"{evidence_id}: recomputed {key} differs from summary")
    for key in ("competition_score_rate", "mean_margin"):
        if not math.isclose(metric[key], expected[key], abs_tol=1e-9):
            raise EvidenceError(f"{evidence_id}: recomputed {key} differs from summary")
    _check_rate_identity(metric, label=evidence_id)
    candidate = str(pair["model_a"])
    anchor = str(pair["model_b"])
    threshold = PURE_WIN_GATE_A2 if anchor == A2 else PURE_WIN_GATE_R002
    inclusive = anchor == A2
    gate_pass = metric["pure_win_rate"] >= threshold if inclusive else metric["pure_win_rate"] > threshold
    result = {
        "evidence_id": evidence_id,
        "evidence_order": evidence_order,
        "label": label,
        "evidence_level": level,
        "candidate": candidate,
        "anchor": anchor,
        **metric,
        "pure_win_gate": threshold,
        "gate_pass_point_estimate": gate_pass,
        "submission_eligible": False,
        "source_path": _repo_path(summary_path),
        "note": "已暴露开发面板；只用于机制选择，不是新鲜确认。",
    }
    slices = _slice_metrics(
        rows,
        margin_getter=_pairwise_game_margin,
        seat_getter=lambda row: int(row.get("model_a_seat", 0)),
        candidate=candidate,
        anchor=anchor,
        evidence_level=level,
        evidence_id=evidence_id,
    )
    return result, slices, [summary_path, games_path]


def _oracle_evidence(
    summary_path: Path,
    games_path: Path,
    *,
    evidence_id: str,
    label: str,
    candidate: str,
    anchor: str,
    evidence_order: int,
    declared_games_sha: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[Path], dict[str, Any]]:
    summary = read_json(summary_path)
    _assert_no_test_flags(summary, source=summary_path)
    rows = read_jsonl(games_path)
    _assert_source_splits(rows, source=games_path)
    metric = _counts_from_margins(_oracle_game_margin(row) for row in rows)
    expected_outcomes = summary.get("outcomes") or (summary.get("oracle") or {}).get("outcomes")
    if expected_outcomes:
        expected = {
            "wins": int(expected_outcomes["W"]),
            "ties": int(expected_outcomes["T"]),
            "losses": int(expected_outcomes["L"]),
        }
        if any(metric[key] != value for key, value in expected.items()):
            raise EvidenceError(f"{evidence_id}: oracle W/T/L recomputation mismatch")
    _check_rate_identity(metric, label=evidence_id)
    result = {
        "evidence_id": evidence_id,
        "evidence_order": evidence_order,
        "label": label,
        "evidence_level": "oracle_exposed",
        "candidate": candidate,
        "anchor": anchor,
        **metric,
        "pure_win_gate": PURE_WIN_GATE_A2,
        "gate_pass_point_estimate": metric["pure_win_rate"] >= PURE_WIN_GATE_A2,
        "submission_eligible": False,
        "source_path": _repo_path(summary_path),
        "note": "perfect-information oracle；读取现实 agent 不可见真值，不可部署。",
    }
    slices = _slice_metrics(
        rows,
        margin_getter=_oracle_game_margin,
        seat_getter=lambda row: int(row.get("candidate_seat", 0)),
        candidate=candidate,
        anchor=anchor,
        evidence_level="oracle_exposed",
        evidence_id=evidence_id,
    )
    closure = {
        "role": f"{evidence_id} declared games",
        "path": _repo_path(games_path),
        "expected_sha256": declared_games_sha,
        "actual_sha256": sha256_file(games_path),
    }
    closure["status"] = (
        "pass"
        if declared_games_sha and closure["actual_sha256"] == declared_games_sha
        else "observed"
        if not declared_games_sha
        else "mismatch"
    )
    return result, slices, [summary_path, games_path], closure


def _fresh_audits() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[Path], list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    slices: list[dict[str, Any]] = []
    files: list[Path] = []
    closure: list[dict[str, Any]] = []
    candidates = sorted(
        path
        for path in V14_DIR.rglob("audit.json")
        if "invalidated" not in path.as_posix().lower()
        and "test" not in path.as_posix().lower()
    )
    seen: set[tuple[str, str, str]] = set()
    for path in candidates:
        payload = read_json(path)
        if payload.get("schema") != "kaggriculture-v14-dual-anchor-audit-1":
            continue
        _assert_no_test_flags(payload, source=path)
        phase = str(payload.get("phase"))
        if phase not in {"screen", "confirmatory"}:
            raise EvidenceError(f"unexpected V14 audit phase in {_repo_path(path)}")
        candidate = str(payload.get("candidate"))
        key = (phase, candidate, str(payload.get("run_fingerprint")))
        if key in seen:
            continue
        seen.add(key)
        checks = (payload.get("protocol_verification") or {}).get("checks") or {}
        if checks and (
            checks.get(f"{phase}_no_test") is not True
            or checks.get("test_outcomes_not_accessed") is not True
        ):
            raise EvidenceError(f"audit lacks no-test proof: {_repo_path(path)}")
        if int(payload.get("error_count") or 0) != 0:
            raise EvidenceError(f"fresh audit contains errors: {_repo_path(path)}")
        expected_rows = int(payload.get("expected_rows") or 0)
        if int(payload.get("rows") or -1) != expected_rows:
            raise EvidenceError(f"fresh audit row closure failed: {_repo_path(path)}")
        by_anchor = payload.get("by_anchor") or {}
        for anchor, anchor_payload in sorted(by_anchor.items()):
            overall = dict(anchor_payload["overall"])
            metric = {
                "games": int(overall["games"]),
                "wins": int(overall["wins"]),
                "ties": int(overall["ties"]),
                "losses": int(overall["losses"]),
                "pure_win_rate": float(overall["pure_win_rate"]),
                "competition_score_rate": float(overall["competition_score_rate"]),
                "mean_margin": float(overall["mean_margin"]),
            }
            _check_rate_identity(metric, label=f"fresh-{phase}-{candidate}-{anchor}")
            threshold = PURE_WIN_GATE_A2 if anchor == A2 else PURE_WIN_GATE_R002
            inclusive = anchor == A2
            gate_pass = metric["pure_win_rate"] >= threshold if inclusive else metric["pure_win_rate"] > threshold
            evidence_id = f"fresh_{phase}_{candidate}_{anchor}"
            evidence.append(
                {
                    "evidence_id": evidence_id,
                    "evidence_order": 300 if phase == "screen" else 400,
                    "label": f"{candidate} {phase} vs {anchor}",
                    "evidence_level": "fresh_screen" if phase == "screen" else "fresh_confirm",
                    "candidate": candidate,
                    "anchor": anchor,
                    **metric,
                    "pure_win_rate_ci95": overall.get("pure_win_rate_ci95"),
                    "competition_score_rate_ci95": overall.get("competition_score_rate_ci95"),
                    "mean_margin_ci95": overall.get("mean_margin_ci95"),
                    "pure_win_gate": threshold,
                    "gate_pass_point_estimate": gate_pass,
                    "submission_eligible": phase == "confirmatory" and payload.get("passed") is True,
                    "source_path": _repo_path(path),
                    "note": "新鲜冻结面板；确认集仅允许唯一 finalist 一次消费。",
                }
            )
            for dimension_key, dimension_name in (
                ("by_date", "date"),
                ("by_candidate_seat", "candidate_seat"),
            ):
                for slice_value, values in sorted((anchor_payload.get(dimension_key) or {}).items()):
                    slice_metric = {
                        "games": int(values["games"]),
                        "wins": int(values["wins"]),
                        "ties": int(values["ties"]),
                        "losses": int(values["losses"]),
                        "pure_win_rate": float(values["pure_win_rate"]),
                        "competition_score_rate": float(values["competition_score_rate"]),
                        "mean_margin": float(values["mean_margin"]),
                    }
                    _check_rate_identity(slice_metric, label=f"{evidence_id}-{dimension_name}-{slice_value}")
                    slices.append(
                        {
                            "evidence_id": evidence_id,
                            "evidence_level": "fresh_screen" if phase == "screen" else "fresh_confirm",
                            "candidate": candidate,
                            "anchor": anchor,
                            "dimension": dimension_name,
                            "slice": str(slice_value),
                            **slice_metric,
                        }
                    )
        files.append(path)
        for field, hash_field, role in (
            ("games", "games_file_sha256", "fresh audit games"),
            ("run_manifest", "run_manifest_file_sha256", "fresh audit run manifest"),
            ("registry", "registry_file_sha256", "fresh audit clean registry"),
            ("panel", "panel_file_sha256", "fresh audit panel"),
        ):
            value = payload.get(field)
            if not value:
                continue
            target = _resolve_artifact_path(value)
            actual = sha256_file(target) if target.is_file() else None
            expected = payload.get(hash_field)
            closure.append(
                {
                    "role": f"{role}: {phase}/{candidate}",
                    "path": _repo_path(target),
                    "expected_sha256": expected,
                    "actual_sha256": actual,
                    "status": "pass" if actual and expected == actual else "missing" if actual is None else "mismatch",
                }
            )
            if target.is_file():
                files.append(target)
    return evidence, slices, files, closure


def _package_qa() -> tuple[list[dict[str, Any]], list[Path], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    files: list[Path] = []
    closure: list[dict[str, Any]] = []
    for path in sorted(MODEL_DIR.glob("v14*/package_qa_report.json")):
        if "first_principles_search" in path.as_posix():
            continue
        payload = read_json(path)
        _assert_no_test_flags(payload, source=path)
        candidate = str(payload.get("candidate") or path.parent.name)
        archive_data = payload.get("archive") or {}
        archive_value = archive_data.get("path")
        archive_path = _resolve_artifact_path(archive_value) if archive_value else path.parent / "submission.tar.gz"
        archive_actual = sha256_file(archive_path) if archive_path.is_file() else None
        archive_expected = archive_data.get("sha256")
        checks = payload.get("checks") or {}
        records.append(
            {
                "candidate": candidate,
                "verdict": str(payload.get("verdict") or "UNKNOWN"),
                "archive_sha256": archive_actual,
                "declared_archive_sha256": archive_expected,
                "archive_size_bytes": archive_data.get("size_bytes"),
                "games": len(payload.get("games") or []),
                "raw_loader_clean": checks.get("real_kaggle_raw_loader_clean_extraction") is True,
                "source_archive_action_reward_exact": checks.get("source_archive_exact_actions_rewards") is True,
                "all_games_done": checks.get("all_720_states_719_calls_done") is True,
                "source_path": _repo_path(path),
            }
        )
        files.append(path)
        if archive_path.is_file():
            files.append(archive_path)
        closure.append(
            {
                "role": f"package archive: {candidate}",
                "path": _repo_path(archive_path),
                "expected_sha256": archive_expected,
                "actual_sha256": archive_actual,
                "status": "pass" if archive_actual and archive_actual == archive_expected else "missing" if archive_actual is None else "mismatch",
            }
        )
        manifest_path = path.parent / "submission_manifest.json"
        if manifest_path.is_file():
            manifest = read_json(manifest_path)
            _assert_no_test_flags(manifest, source=manifest_path)
            files.append(manifest_path)
            declared = manifest.get("archive_sha256")
            closure.append(
                {
                    "role": f"submission manifest archive: {candidate}",
                    "path": _repo_path(archive_path),
                    "expected_sha256": declared,
                    "actual_sha256": archive_actual,
                    "status": "pass" if archive_actual and archive_actual == declared else "missing" if archive_actual is None else "mismatch",
                }
            )
    return records, files, closure


def _shadow_qa() -> tuple[dict[str, Any], list[Path], list[dict[str, Any]]]:
    preferred = V14_DIR / "shadow_qa" / "exact_a2_shadow_q2b_qa.json"
    fallback = V14_DIR / "shadow_qa" / "exact_a2_shadow_no_mirror_qa.json"
    path = preferred if preferred.is_file() else fallback
    payload = read_json(path)
    _assert_no_test_flags(payload, source=path)
    aggregate = payload["aggregate"]
    record = {
        "candidate": (payload.get("variant") or {}).get("model_id", "v14_queue_stateful_no_mirror"),
        "games": int(aggregate["games"]),
        "compared_calls": int(aggregate["compared_calls"]),
        "private_exact_calls": int(aggregate["private_exact_calls"]),
        "private_exact_rate": float(aggregate["private_exact_rate"]),
        "action_exact_calls": int(aggregate["action_exact_calls"]),
        "action_exact_rate": float(aggregate["action_exact_rate"]),
        "day_boundary_calls": int(aggregate["day_boundary_calls"]),
        "day_boundary_private_exact_calls": int(aggregate["day_boundary_private_exact_calls"]),
        "day_boundary_action_exact_calls": int(aggregate["day_boundary_action_exact_calls"]),
        "reordered_steps": int(aggregate["candidate_reordered_steps"]),
        "shadow_faults": int(aggregate["candidate_shadow_faults"]),
        "shadow_update_errors": int(aggregate["candidate_shadow_update_errors"]),
        "go": payload.get("go") is True,
        "scope": "exact A2 only; not unknown-opponent identification",
        "source_path": _repo_path(path),
    }
    closure: list[dict[str, Any]] = []
    files = [path]
    for key, expected in (payload.get("artifacts") or {}).items():
        if not key.endswith("_sha256") or not isinstance(expected, str):
            continue
        path_key = key.removesuffix("_sha256") + "_path"
        path_value = (payload.get("artifacts") or {}).get(path_key)
        if not path_value:
            continue
        target = _resolve_artifact_path(path_value)
        actual = sha256_file(target) if target.is_file() else None
        closure.append(
            {
                "role": f"shadow QA {key.removesuffix('_sha256')}",
                "path": _repo_path(target),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "status": "pass" if actual and actual == expected else "missing" if actual is None else "mismatch",
            }
        )
        if target.is_file():
            files.append(target)
    return record, files, closure


def _shadow_calibration() -> tuple[dict[str, Any], list[Path], list[dict[str, Any]]]:
    path = V14_DIR / "shadow_calibration" / "combined_summary.json"
    payload = read_json(path)
    _assert_no_test_flags(payload, source=path)
    method_b = (payload.get("methods") or {}).get("B") or {}
    overall = method_b.get("overall") or {}
    gate = payload.get("recommended_preregistered_gate") or {}
    record = {
        "games": int(payload.get("games") or 0),
        "opportunities": int(payload.get("opportunities") or 0),
        "method": str(method_b.get("name") or "B flow-corrected"),
        "queue_exact_rate": float((overall.get("queue_exact") or {}).get("rate") or 0.0),
        "shed_exact_rate": float((overall.get("shed_exact") or {}).get("rate") or 0.0),
        "exec_cap_exact_rate": float((overall.get("actual_queue_exec_cap_exact") or {}).get("rate") or 0.0),
        "gate": gate.get("gate"),
        "gate_coverage": gate.get("coverage"),
        "gate_queue_precision": gate.get("queue_precision"),
        "gate_queue_wilson95_lower": gate.get("queue_wilson95_lower"),
        "epistemic_status": payload.get("epistemic_status"),
        "source_path": _repo_path(path),
    }
    closure: list[dict[str, Any]] = []
    files = [path]
    for file_field, sha_field in (
        ("games_file", "games_sha256"),
        ("opportunities_file", "opportunities_sha256"),
        ("coverage_precision_csv", "coverage_precision_csv_sha256"),
        ("segment_metrics_csv", "segment_metrics_csv_sha256"),
    ):
        value = payload.get(file_field)
        expected = payload.get(sha_field)
        if not value:
            continue
        target = _resolve_artifact_path(value)
        actual = sha256_file(target) if target.is_file() else None
        closure.append(
            {
                "role": f"shadow calibration {file_field}",
                "path": _repo_path(target),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "status": "pass" if actual and actual == expected else "missing" if actual is None else "mismatch",
            }
        )
        if target.is_file():
            files.append(target)
    return record, files, closure


def _oracle_gap() -> tuple[dict[str, Any], list[Path]]:
    ablation_path = V14_DIR / "oracle_gap" / "public_equality_ablation.json"
    alignment_path = V14_DIR / "oracle_gap" / "task_alignment.json"
    ablation = read_json(ablation_path)
    alignment = read_json(alignment_path)
    _assert_no_test_flags(ablation, source=ablation_path)
    _assert_no_test_flags(alignment, source=alignment_path)
    outcomes = ablation["outcomes"]
    record = {
        "games": int(ablation["games"]),
        "wins": int(outcomes["W"]),
        "ties": int(outcomes["T"]),
        "losses": int(outcomes["L"]),
        "pure_win_rate": float(ablation["pure_win_rate"]),
        "competition_score_rate": float(ablation["score_rate"]),
        "reordered_steps": int(ablation["reordered_steps"]),
        "shadow_faults": int(ablation["shadow_faults"]),
        "shadow_update_errors": int(ablation["shadow_update_errors"]),
        "all_shadow_trusted": ablation["all_shadow_trusted"] is True,
        "reward_vectors_exact_oracle": int(ablation["reward_vectors_exact_oracle"]),
        "oracle_to_stateful": alignment.get("oracle_to_stateful"),
        "oracle_to_ablation": alignment.get("oracle_to_public_equality_ablation"),
        "stateful_reordered_steps": int(alignment["stateful_reordered_steps"]),
        "ablation_reordered_steps": int(alignment["ablation_reordered_steps"]),
        "source_paths": [_repo_path(ablation_path), _repo_path(alignment_path)],
    }
    _check_rate_identity(record, label="oracle-gap-ablation")
    return record, [ablation_path, alignment_path]


def _protocol() -> tuple[dict[str, Any], list[Path], list[dict[str, Any]]]:
    contract_path = VALIDATION_DIR / "evaluation_contract.json"
    seal_path = VALIDATION_DIR / "panel_seal.json"
    contract = read_json(contract_path)
    seal = read_json(seal_path)
    _assert_no_test_flags(contract, source=contract_path)
    _assert_no_test_flags(seal, source=seal_path)
    if seal.get("test_access") is not False:
        raise EvidenceError("V14 panel seal does not prove test_access=false")
    if int(seal.get("screen_test_source_count") or 0) != 0 or int(seal.get("confirmatory_test_source_count") or 0) != 0:
        raise EvidenceError("V14 panel seal contains test sources")
    record = {
        "status": seal.get("status"),
        "candidate_archives_sealed": seal.get("candidate_archives_sealed") is True,
        "environment_games_started": seal.get("environment_games_started") is True,
        "test_access": seal.get("test_access"),
        "screen_records_sha256": seal.get("screen_records_sha256"),
        "confirmatory_records_sha256": seal.get("confirmatory_records_sha256"),
        "screen_confirmatory_disjoint": seal.get("screen_confirmatory_disjoint") is True,
        "exposure_union_seed_count": int(seal.get("exposure_union_seed_count") or 0),
        "hard_gates": contract.get("hard_gates"),
        "task_design": contract.get("task_design"),
        "source_paths": [_repo_path(contract_path), _repo_path(seal_path)],
    }
    files = [contract_path, seal_path]
    closure: list[dict[str, Any]] = []
    for asset in seal.get("assets") or []:
        target = _resolve_artifact_path(asset["path"])
        expected = asset.get("file_sha256")
        actual = sha256_file(target) if target.is_file() else None
        closure.append(
            {
                "role": "frozen validation protocol asset",
                "path": _repo_path(target),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "status": "pass" if actual and actual == expected else "missing" if actual is None else "mismatch",
            }
        )
        if target.is_file():
            files.append(target)
    return record, files, closure


def _online_submission(explicit: Path | None = None) -> tuple[list[dict[str, Any]], list[Path]]:
    candidates: list[Path] = []
    if explicit is not None:
        candidates = [explicit.resolve()]
    else:
        patterns = (
            "kaggle_submission*.json",
            "submission_status*.json",
            "submission_result*.json",
            "submission_record*.json",
        )
        roots = [V14_DIR, *sorted(MODEL_DIR.glob("v14*"))]
        for root in roots:
            if not root.is_dir():
                continue
            for pattern in patterns:
                candidates.extend(root.rglob(pattern))
    records: list[dict[str, Any]] = []
    files: list[Path] = []
    for path in sorted(set(candidates)):
        if not path.is_file() or "test" in path.as_posix().lower():
            continue
        _resolve_artifact_path(path)
        payload = read_json(path)
        _assert_no_test_flags(payload, source=path)
        rows = payload if isinstance(payload, list) else [payload]
        for row in rows:
            if not isinstance(row, dict):
                continue
            submission_id = row.get("submission_id") or row.get("id") or row.get("ref")
            status = row.get("status") or row.get("state")
            score = row.get("rating")
            if score is None:
                score = row.get("score")
            if score is None:
                score = row.get("public_score")
            if submission_id is None and status is None and score is None:
                continue
            records.append(
                {
                    "submission_id": str(submission_id) if submission_id is not None else None,
                    "status": str(status) if status is not None else None,
                    "score_or_rating": float(score) if isinstance(score, (int, float)) else score,
                    "description": row.get("description") or row.get("message"),
                    "submitted_at": row.get("submitted_at") or row.get("date") or row.get("created_at"),
                    "archive_sha256": row.get("archive_sha256") or row.get("file_sha256"),
                    "source_path": _repo_path(path),
                    "source_file_sha256": sha256_file(path),
                }
            )
        files.append(path)
    return records, files


def collect_evidence(*, submission_json: Path | None = None) -> dict[str, Any]:
    """Build a bounded, audited snapshot used by both notebook and HTML report."""

    evidence_rows: list[dict[str, Any]] = []
    slice_rows: list[dict[str, Any]] = []
    loaded_files: list[Path] = []
    closure_rows: list[dict[str, Any]] = []

    strict_summary_path = V14_DIR / "oracle" / "strict_summary.json"
    strict_summary = read_json(strict_summary_path)
    oracle_row, oracle_slices, files, closure = _oracle_evidence(
        strict_summary_path,
        V14_DIR / "oracle" / "strict_games.jsonl",
        evidence_id="oracle_v13c_vs_a2",
        label="Perfect-info oracle (V13C parent) vs A2",
        candidate="perfect_info_queue_oracle_v13c_parent",
        anchor=A2,
        evidence_order=10,
        declared_games_sha=strict_summary.get("games_sha256"),
    )
    evidence_rows.append(oracle_row)
    slice_rows.extend(oracle_slices)
    loaded_files.extend(files)
    closure_rows.append(closure)

    a2_oracle_summary_path = V14_DIR / "oracle" / "a2_parent_summary.json"
    a2_oracle_summary = read_json(a2_oracle_summary_path)
    oracle_row, oracle_slices, files, closure = _oracle_evidence(
        a2_oracle_summary_path,
        V14_DIR / "oracle" / "a2_parent_oracle_games.jsonl",
        evidence_id="oracle_a2_parent_vs_a2",
        label="Perfect-info oracle (A2 parent) vs A2",
        candidate="perfect_info_queue_oracle_a2_parent",
        anchor=A2,
        evidence_order=20,
        declared_games_sha=a2_oracle_summary.get("oracle_games_sha256"),
    )
    evidence_rows.append(oracle_row)
    slice_rows.extend(oracle_slices)
    loaded_files.extend(files)
    closure_rows.append(closure)
    baseline_games = V14_DIR / "oracle" / "a2_parent_baseline_games.jsonl"
    closure_rows.append(
        {
            "role": "A2-parent oracle baseline games",
            "path": _repo_path(baseline_games),
            "expected_sha256": a2_oracle_summary.get("baseline_games_sha256"),
            "actual_sha256": sha256_file(baseline_games),
            "status": "pass" if sha256_file(baseline_games) == a2_oracle_summary.get("baseline_games_sha256") else "mismatch",
        }
    )
    loaded_files.append(baseline_games)

    dev_specs = [
        (
            V14_DIR / "dev_runs" / "queue_solver_stateful_screen36" / "summary.json",
            "dev_q1_vs_a2",
            "Q1 stateful shadow vs A2",
            100,
        ),
        (
            V14_DIR / "dev_runs" / "queue_solver_stateful_vs_r002_screen36" / "summary.json",
            "dev_q1_vs_r002",
            "Q1 stateful shadow vs r002",
            110,
        ),
        (
            V14_DIR / "dev_runs" / "queue_s1_vs_a2_screen36_retry2" / "summary.json",
            "dev_q1_s1_vs_a2",
            "Q1 + S1 vs A2",
            120,
        ),
        (
            V14_DIR / "dev_runs" / "queue_s1_vs_r002_screen36_retry2" / "summary.json",
            "dev_q1_s1_vs_r002",
            "Q1 + S1 vs r002",
            130,
        ),
        (
            V14_DIR / "dev_runs" / "q2b_no_public_equal_vs_a2_screen36" / "summary.json",
            "dev_q2b_vs_a2",
            "Q2b no-public-equality vs A2",
            140,
        ),
        (
            V14_DIR / "dev_runs" / "q2b_no_public_equal_vs_r002_screen36" / "summary.json",
            "dev_q2b_vs_r002",
            "Q2b no-public-equality vs r002",
            150,
        ),
    ]
    for summary_path, evidence_id, label, order in dev_specs:
        row, slices, files = _pairwise_evidence(
            summary_path,
            evidence_id=evidence_id,
            label=label,
            evidence_order=order,
        )
        evidence_rows.append(row)
        slice_rows.extend(slices)
        loaded_files.extend(files)

    alternative_summary = V14_DIR / "alternatives" / "runs" / "screen36_s1" / "summary.json"
    alternative_games = alternative_summary.with_name("games.jsonl")
    alternative = read_json(alternative_summary)
    _assert_no_test_flags(alternative, source=alternative_summary)
    alternative_rows = read_jsonl(alternative_games)
    _assert_source_splits(alternative_rows, source=alternative_games)
    for anchor, order in ((A2, 90), (R002, 95)):
        anchor_rows = [row for row in alternative_rows if row.get("model_b") == anchor]
        metric = _counts_from_margins(_pairwise_game_margin(row) for row in anchor_rows)
        _check_rate_identity(metric, label=f"dev-s1-{anchor}")
        threshold = PURE_WIN_GATE_A2 if anchor == A2 else PURE_WIN_GATE_R002
        evidence_id = f"dev_s1_vs_{'a2' if anchor == A2 else 'r002'}"
        evidence_rows.append(
            {
                "evidence_id": evidence_id,
                "evidence_order": order,
                "label": f"S1 inventory-neutral WHEAT squeeze vs {anchor}",
                "evidence_level": "dev_exposed",
                "candidate": "v14_s1_inventory_neutral_wheat_squeeze",
                "anchor": anchor,
                **metric,
                "pure_win_gate": threshold,
                "gate_pass_point_estimate": metric["pure_win_rate"] >= threshold if anchor == A2 else metric["pure_win_rate"] > threshold,
                "submission_eligible": False,
                "source_path": _repo_path(alternative_summary),
                "note": "已暴露开发面板；单独 S1 未通过 A2 纯胜率门。",
            }
        )
        slice_rows.extend(
            _slice_metrics(
                anchor_rows,
                margin_getter=_pairwise_game_margin,
                seat_getter=lambda row: int(row.get("model_a_seat", 0)),
                candidate="v14_s1_inventory_neutral_wheat_squeeze",
                anchor=anchor,
                evidence_level="dev_exposed",
                evidence_id=evidence_id,
            )
        )
    loaded_files.extend([alternative_summary, alternative_games])

    oracle_gap, files = _oracle_gap()
    loaded_files.extend(files)
    shadow_qa, files, closure = _shadow_qa()
    loaded_files.extend(files)
    closure_rows.extend(closure)
    shadow_calibration, files, closure = _shadow_calibration()
    loaded_files.extend(files)
    closure_rows.extend(closure)
    packages, files, closure = _package_qa()
    loaded_files.extend(files)
    closure_rows.extend(closure)
    protocol, files, closure = _protocol()
    loaded_files.extend(files)
    closure_rows.extend(closure)
    fresh_rows, fresh_slices, files, closure = _fresh_audits()
    evidence_rows.extend(fresh_rows)
    slice_rows.extend(fresh_slices)
    loaded_files.extend(files)
    closure_rows.extend(closure)
    online, files = _online_submission(submission_json)
    loaded_files.extend(files)

    community_path = V14_DIR / "community_frontier.md"
    design_path = V14_DIR / "game_theory_design.md"
    redteam_path = V14_DIR / "queue_solver_redteam.md"
    decision_path = V14_DIR / "decision_log.md"
    loaded_files.extend([community_path, design_path, redteam_path, decision_path])

    dedup_files = sorted({path.resolve() for path in loaded_files if path.is_file()})
    source_inventory = [
        {
            "path": _repo_path(path),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
        for path in dedup_files
    ]
    declared_checks = [row for row in closure_rows if row.get("expected_sha256")]
    closure_ok = all(row.get("status") == "pass" for row in declared_checks)

    q2b_a2 = next(row for row in evidence_rows if row["evidence_id"] == "dev_q2b_vs_a2")
    q2b_r002 = next(row for row in evidence_rows if row["evidence_id"] == "dev_q2b_vs_r002")
    fresh_confirm = [row for row in evidence_rows if row["evidence_level"] == "fresh_confirm"]
    fresh_screen = [row for row in evidence_rows if row["evidence_level"] == "fresh_screen"]
    confirm_candidates = defaultdict(list)
    for row in fresh_confirm:
        confirm_candidates[row["candidate"]].append(row)
    confirm_passed = [
        candidate
        for candidate, rows in confirm_candidates.items()
        if len(rows) == 2 and all(row["submission_eligible"] for row in rows)
    ]
    package_ready = any(
        row["candidate"] == "v14_queue_stateful_no_mirror"
        and row["verdict"] == "PASS"
        and row["raw_loader_clean"]
        and row["source_archive_action_reward_exact"]
        for row in packages
    )
    if online:
        overall_status = "online evidence present; inspect Kaggle status separately"
    elif confirm_passed and closure_ok and package_ready:
        overall_status = "fresh confirm passed; locally eligible for submission"
    elif fresh_confirm:
        overall_status = "fresh confirm exists but the hard gate did not fully pass"
    elif fresh_screen:
        overall_status = "fresh screen available; confirmatory conclusion pending"
    else:
        overall_status = "development evidence only; no fresh 65% submission conclusion"

    evidence_rows.sort(key=lambda row: (int(row["evidence_order"]), row["label"]))
    slice_rows.sort(
        key=lambda row: (
            row["evidence_level"],
            row["candidate"],
            row["anchor"],
            row["dimension"],
            row["slice"],
        )
    )
    return {
        "schema": "kaggriculture-v14-report-snapshot-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "dates": ["2026-08-18", "2026-08-19", "2026-08-20"],
            "allowed_splits": sorted(ALLOWED_SPLITS),
            "test_outcomes_read": False,
            "new_games_started": False,
            "kaggle_api_called": False,
            "metric_definitions": {
                "pure_win_rate": "wins / all games; ties remain in denominator and are not wins",
                "competition_score_rate": "(wins + 0.5 * ties) / all games; report-only",
                "mean_margin": "candidate terminal reward minus anchor terminal reward",
            },
        },
        "overall_status": overall_status,
        "submission_decision": {
            "fresh_confirm_candidates_passing": sorted(confirm_passed),
            "package_ready_q2b": package_ready,
            "declared_hash_closure_pass": closure_ok,
            "online_record_count": len(online),
            "unknown_opponent_identity_proven": False,
        },
        "evidence_rows": evidence_rows,
        "slice_rows": slice_rows,
        "q2b_headline": {"vs_a2": q2b_a2, "vs_r002": q2b_r002},
        "oracle_gap": oracle_gap,
        "shadow_qa": shadow_qa,
        "shadow_calibration": shadow_calibration,
        "packages": packages,
        "protocol": protocol,
        "online_submissions": online,
        "community_findings": [
            {
                "topic": "737128 MELON tree",
                "finding": "观测式未来价格预测不等于动作反事实；不直接移植。",
                "evidence_status": "community self-report + local mechanism review",
            },
            {
                "topic": "737027 opponent inventory",
                "finding": "可识别商品应做区间/残差跟踪；地板、DROP、overflow 时保持不确定。",
                "evidence_status": "community self-report",
            },
            {
                "topic": "736439 non-transitive experts",
                "finding": "支持条件 payoff / best response，不支持静态平均混合。",
                "evidence_status": "community self-report",
            },
            {
                "topic": "734412 market semantics",
                "finding": "共享市场、需求钟与 slot 顺序是直接交互通道。",
                "evidence_status": "community + official-engine verification",
            },
        ],
        "hash_closure": closure_rows,
        "source_inventory": source_inventory,
    }


def compact_status(snapshot: dict[str, Any]) -> str:
    q2b = snapshot["q2b_headline"]
    a2 = q2b["vs_a2"]
    r002 = q2b["vs_r002"]
    return (
        f"{snapshot['overall_status']}\n"
        f"Q2b exposed vs A2: {a2['wins']}/{a2['ties']}/{a2['losses']} "
        f"(pure {a2['pure_win_rate']:.2%}, score {a2['competition_score_rate']:.2%}); "
        f"vs r002: {r002['wins']}/{r002['ties']}/{r002['losses']} "
        f"(pure {r002['pure_win_rate']:.2%}, score {r002['competition_score_rate']:.2%})."
    )


if __name__ == "__main__":
    print(json.dumps(collect_evidence(), ensure_ascii=False, indent=2, sort_keys=True))
