"""Fail-closed V14 result auditor with pure-win gates and clustered intervals."""

from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np

from common import ANCHORS, HERE, file_sha256, finite_number, load_json
from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as v10
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    load_registry,
    registry_fingerprint,
)
from run_dual_anchor import (
    SCHEMA,
    build_tasks,
    clean_registry_or_fail,
    load_panel,
    load_slate,
    run_fingerprint as expected_run_fingerprint,
    validate_row_against_task,
)
from seal_candidates import CANDIDATE_SEAL, CANDIDATE_SLATE, CLEAN_REGISTRY
from verify_protocol import verify


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"duplicate JSON key: {key}")
        payload[key] = value
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line, object_pairs_hook=unique_object)
            except json.JSONDecodeError as exc:
                raise ValueError(f"malformed JSONL at line {line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"non-object JSONL row at line {line_number}")
            row["_physical_line"] = line_number
            rows.append(row)
    return rows


def source_key(source: Mapping[str, Any]) -> tuple[str, int, str, str]:
    split = str(source.get("split") or "").lower()
    if split == "val":
        split = "validation"
    return (
        str(source.get("date") or "")[:10],
        int(source["seed"]),
        str(source.get("episode_id") or ""),
        split,
    )


def stable_rng_seed(label: str) -> int:
    return int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:8], "big")


def bootstrap_ci(
    values: list[float], dates: list[str], label: str, rounds: int = 10_000
) -> list[float]:
    if not values or len(values) != len(dates):
        raise ValueError("bootstrap values/dates mismatch")
    array = np.asarray(values, dtype=np.float64)
    groups = [
        np.asarray([index for index, date in enumerate(dates) if date == wanted], dtype=np.int64)
        for wanted in sorted(set(dates))
    ]
    rng = np.random.default_rng(stable_rng_seed(label))
    estimates = np.empty(rounds, dtype=np.float64)
    for index in range(rounds):
        sampled = np.concatenate([rng.choice(group, size=len(group), replace=True) for group in groups])
        estimates[index] = float(array[sampled].mean())
    return [float(np.quantile(estimates, 0.025)), float(np.quantile(estimates, 0.975))]


def candidate_values(
    row: Mapping[str, Any], candidate: str
) -> tuple[int, float, float, int]:
    model_a = str(row["model_a"])
    model_b = str(row["model_b"])
    model_a_seat = int(row["model_a_seat"])
    rewards = [float(value) for value in row["rewards"]]
    if model_a == candidate:
        candidate_seat = model_a_seat
    elif model_b == candidate:
        candidate_seat = 1 - model_a_seat
    else:
        raise ValueError(f"candidate absent on line {row.get('_physical_line', '?')}")
    reward = rewards[candidate_seat]
    opponent_reward = rewards[1 - candidate_seat]
    margin = reward - opponent_reward
    outcome = 1 if margin > 0 else -1 if margin < 0 else 0
    score = 1.0 if outcome > 0 else 0.0 if outcome < 0 else 0.5
    return outcome, score, margin, candidate_seat


def game_summary(rows: list[dict[str, Any]], candidate: str) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot summarize an empty game slice")
    values = [candidate_values(row, candidate) for row in rows]
    outcomes = [value[0] for value in values]
    scores = [value[1] for value in values]
    margins = [value[2] for value in values]
    return {
        "games": len(rows),
        "wins": sum(value > 0 for value in outcomes),
        "ties": sum(value == 0 for value in outcomes),
        "losses": sum(value < 0 for value in outcomes),
        "pure_win_rate": float(np.mean([value > 0 for value in outcomes])),
        "competition_score_rate": float(np.mean(scores)),
        "mean_margin": float(np.mean(margins)),
    }


def cluster_metric(
    grouped: Mapping[tuple[str, int, str, str], list[dict[str, Any]]],
    candidate: str,
    extractor: Callable[[int, float, float], float],
) -> tuple[list[float], list[str]]:
    values: list[float] = []
    dates: list[str] = []
    for key in sorted(grouped):
        rows = grouped[key]
        if len(rows) != 2:
            raise ValueError(f"source cluster does not have two seats: {key}")
        metrics = []
        for row in rows:
            outcome, score, margin, _ = candidate_values(row, candidate)
            metrics.append(float(extractor(outcome, score, margin)))
        values.append(float(np.mean(metrics)))
        dates.append(key[0])
    return values, dates


def anchor_report(
    rows: list[dict[str, Any]], candidate: str, anchor: str, phase: str
) -> dict[str, Any]:
    grouped: dict[tuple[str, int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[source_key(row["source"])].append(row)
    win_values, dates = cluster_metric(grouped, candidate, lambda outcome, score, margin: float(outcome > 0))
    score_values, _ = cluster_metric(grouped, candidate, lambda outcome, score, margin: score)
    margin_values, _ = cluster_metric(grouped, candidate, lambda outcome, score, margin: margin)
    overall = game_summary(rows, candidate)
    overall.update(
        {
            "source_clusters": len(grouped),
            "pure_win_rate_ci95": bootstrap_ci(win_values, dates, f"{phase}:{candidate}:{anchor}:pure-win"),
            "competition_score_rate_ci95": bootstrap_ci(score_values, dates, f"{phase}:{candidate}:{anchor}:score"),
            "mean_margin_ci95": bootstrap_ci(margin_values, dates, f"{phase}:{candidate}:{anchor}:margin"),
        }
    )
    by_date = {
        date: game_summary(
            [row for row in rows if source_key(row["source"])[0] == date], candidate
        )
        for date in sorted(set(dates))
    }
    by_seat = {
        str(seat): game_summary(
            [row for row in rows if candidate_values(row, candidate)[3] == seat], candidate
        )
        for seat in (0, 1)
    }
    return {"anchor": anchor, "overall": overall, "by_date": by_date, "by_candidate_seat": by_seat}


def _validate_consume_lock(
    phase: str,
    candidate: str,
    fingerprint: str,
    games: Path,
    run_manifest: Path,
    registry: Any,
) -> Path:
    lock_path = (
        HERE / "execution_state" / "screen" / f"{candidate}.json"
        if phase == "screen"
        else HERE / "execution_state" / "confirmatory_consumed.json"
    )
    lock = load_json(lock_path)
    expected = {
        "schema": "kaggriculture-v14-panel-consume-lock-1",
        "phase": phase,
        "candidate": candidate,
        "run_fingerprint": fingerprint,
        "registry": str(registry.path),
        "jsonl": str(games.resolve()),
        "run_manifest": str(run_manifest.resolve()),
        "run_manifest_file_sha256": file_sha256(run_manifest),
        "registry_and_code_sha256": registry_fingerprint(registry),
        "panel_file_sha256": file_sha256(
            HERE / ("screen_panel.json" if phase == "screen" else "confirmatory_panel.json")
        ),
        "candidate_seal_file_sha256": file_sha256(CANDIDATE_SEAL),
        "panel": str(panel_path.resolve()),
    }
    if lock != expected:
        raise ValueError("consume lock differs from the exact audited run")
    return lock_path


def audit(
    phase: str,
    candidate: str,
    games: Path,
    run_manifest_path: Path,
    registry_path: Path = CLEAN_REGISTRY,
) -> dict[str, Any]:
    protocol_verification = verify(require_candidates=True)
    slate = load_slate()
    if candidate not in slate["candidate_order"]:
        raise ValueError("candidate is absent from the exact sealed slate")
    panel_path, panel, panel_records = load_panel(phase)
    expected_sources = {source_key(row) for row in panel["records"]}
    registry = load_registry(registry_path.resolve())
    clean_registry_or_fail(registry_path.resolve(), registry)
    fingerprint = expected_run_fingerprint(phase, candidate, registry, panel_path, panel, panel_records)
    tasks = build_tasks(registry, candidate, panel_records, fingerprint)
    expected_by_id = {str(task["task_id"]): task for task in tasks}
    if len(expected_by_id) != len(tasks):
        raise ValueError("expected task IDs are not unique")

    run_manifest = load_json(run_manifest_path)
    manifest_expectations = {
        "schema": SCHEMA,
        "phase": phase,
        "candidate": candidate,
        "anchors": list(ANCHORS),
        "run_fingerprint": fingerprint,
        "registry": str(registry.path),
        "registry_file_sha256": file_sha256(registry_path),
        "registry_and_serving_code_sha256": registry_fingerprint(registry),
        "v10_evaluation_implementation_sha256": v10.implementation_fingerprint(),
        "evaluation_contract_file_sha256": file_sha256(HERE / "evaluation_contract.json"),
        "panel_seal_file_sha256": file_sha256(HERE / "panel_seal.json"),
        "candidate_slate_file_sha256": file_sha256(CANDIDATE_SLATE),
        "candidate_slate_core_sha256": slate["slate_core_sha256"],
        "candidate_seal_file_sha256": file_sha256(CANDIDATE_SEAL),
        "panel": str(panel_path.resolve()),
        "panel_file_sha256": file_sha256(panel_path),
        "panel_records_sha256": panel["records_sha256"],
        "sources": len(panel_records),
        "targeted_pairs": [[candidate, anchor] for anchor in ANCHORS],
        "expected_games": len(tasks),
        "protocol_verification_status": "PASS",
        "confirmatory_execution_flag": phase == "confirmatory",
        "dry_run": False,
    }
    mismatches = {
        key: {"observed": run_manifest.get(key), "expected": value}
        for key, value in manifest_expectations.items()
        if run_manifest.get(key) != value
    }
    if mismatches:
        raise ValueError(f"run manifest differs from exact task definition: {mismatches}")
    lock_path = _validate_consume_lock(
        phase, candidate, fingerprint, games, run_manifest_path, registry
    )

    rows = read_jsonl(games)
    if candidate in ANCHORS:
        raise ValueError("candidate collides with an anchor")
    allowed_pairs = {frozenset((candidate, anchor)) for anchor in ANCHORS}
    observed: set[str] = set()
    grouped: dict[tuple[str, tuple[str, int, str, str]], list[dict[str, Any]]] = defaultdict(list)
    status_counts: Counter[str] = Counter()
    for row in rows:
        line = int(row["_physical_line"])
        task_id = str(row.get("task_id") or "")
        if not task_id or task_id in observed or task_id not in expected_by_id:
            raise ValueError(f"missing/duplicate/foreign task ID at line {line}: {task_id!r}")
        validate_row_against_task(row, expected_by_id[task_id])
        observed.add(task_id)
        pair = frozenset((str(row.get("model_a")), str(row.get("model_b"))))
        if pair not in allowed_pairs:
            raise ValueError(f"unexpected model pair at line {line}: {sorted(pair)}")
        source = source_key(row.get("source") or {})
        if source not in expected_sources:
            raise ValueError(f"unknown source at line {line}: {source}")
        status_counts["/".join(str(value) for value in row["statuses"])] += 1
        candidate_values(row, candidate)
        anchor = next(anchor for anchor in ANCHORS if anchor in pair)
        grouped[(anchor, source)].append(row)

    expected_ids = set(expected_by_id)
    if observed != expected_ids:
        missing = sorted(expected_ids - observed)
        extra = sorted(observed - expected_ids)
        raise ValueError(f"exact task closure failed: missing={missing[:3]} extra={extra[:3]}")
    expected_games = len(expected_sources) * len(ANCHORS) * 2
    if len(rows) != expected_games:
        raise ValueError(f"row closure failed: {len(rows)} != {expected_games}")
    for anchor in ANCHORS:
        for source in expected_sources:
            values = grouped.get((anchor, source), [])
            if len(values) != 2:
                raise ValueError(f"pair/source closure failed: {anchor} {source} rows={len(values)}")
            seats = {candidate_values(row, candidate)[3] for row in values}
            if seats != {0, 1}:
                raise ValueError(f"candidate seat closure failed: {anchor} {source} seats={seats}")

    by_anchor: dict[str, Any] = {}
    for anchor in ANCHORS:
        anchor_rows = [
            row
            for row in rows
            if frozenset((str(row["model_a"]), str(row["model_b"])))
            == frozenset((candidate, anchor))
        ]
        by_anchor[anchor] = anchor_report(anchor_rows, candidate, anchor, phase)
    r002 = by_anchor[ANCHORS[0]]["overall"]
    a2 = by_anchor[ANCHORS[1]]["overall"]
    gates = {
        "integrity": True,
        "a2_pure_win_rate_gte_0_65": a2["pure_win_rate"] >= 0.65,
        "r002_pure_win_rate_gt_0_50": r002["pure_win_rate"] > 0.50,
    }
    return {
        "schema": "kaggriculture-v14-dual-anchor-audit-1",
        "phase": phase,
        "candidate": candidate,
        "anchors": list(ANCHORS),
        "panel": str(panel_path.resolve()),
        "panel_file_sha256": file_sha256(panel_path),
        "panel_records_sha256": panel["records_sha256"],
        "protocol_verification": protocol_verification,
        "games": str(games.resolve()),
        "games_file_sha256": file_sha256(games),
        "run_manifest": str(run_manifest_path.resolve()),
        "run_manifest_file_sha256": file_sha256(run_manifest_path),
        "consume_lock": str(lock_path.resolve()),
        "consume_lock_file_sha256": file_sha256(lock_path),
        "registry": str(registry_path.resolve()),
        "registry_file_sha256": file_sha256(registry_path),
        "run_fingerprint": fingerprint,
        "rows": len(rows),
        "expected_rows": expected_games,
        "source_clusters_per_anchor": len(expected_sources),
        "status_counts": dict(status_counts),
        "error_count": 0,
        "done_done_count": status_counts.get("DONE/DONE", 0),
        "by_anchor": by_anchor,
        "gates": gates,
        "passed": all(gates.values()),
        "metric_note": (
            "Hard gates use wins/all-games pure win rate. Ties are not wins. "
            "Competition score rate and all CIs are reported separately and never substitute for that gate."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("screen", "confirmatory"), required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--games", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=CLEAN_REGISTRY)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = audit(
        args.phase,
        args.candidate,
        args.games.resolve(),
        args.run_manifest.resolve(),
        args.registry.resolve(),
    )
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite an audit: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
