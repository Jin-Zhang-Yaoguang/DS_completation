"""Fail-closed result auditor for one V13 candidate against r002 and A2."""

from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import numpy as np

from freeze_protocol import HERE, file_sha256, verify
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import load_registry
from run_dual_anchor import (
    build_tasks,
    clean_registry_or_fail,
    load_panel,
    load_slate,
    run_fingerprint as expected_run_fingerprint,
    validate_row_against_task,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as v10


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


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


def finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
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
        np.asarray([i for i, date in enumerate(dates) if date == wanted], dtype=np.int64)
        for wanted in sorted(set(dates))
    ]
    rng = np.random.default_rng(stable_rng_seed(label))
    estimates = np.empty(rounds, dtype=np.float64)
    for index in range(rounds):
        sampled = np.concatenate(
            [rng.choice(group, size=len(group), replace=True) for group in groups]
        )
        estimates[index] = float(array[sampled].mean())
    return [
        float(np.quantile(estimates, 0.025)),
        float(np.quantile(estimates, 0.975)),
    ]


def candidate_values(
    row: Mapping[str, Any], candidate: str
) -> tuple[int, float, float, int]:
    model_a = str(row["model_a"])
    model_b = str(row["model_b"])
    a_seat = int(row["model_a_seat"])
    rewards = [float(value) for value in row["rewards"]]
    if model_a == candidate:
        candidate_seat = a_seat
        reward = rewards[a_seat]
        opponent_reward = rewards[1 - a_seat]
    elif model_b == candidate:
        candidate_seat = 1 - a_seat
        reward = rewards[1 - a_seat]
        opponent_reward = rewards[a_seat]
    else:
        raise ValueError(f"candidate absent on line {row['_physical_line']}")
    margin = reward - opponent_reward
    outcome = 1 if margin > 0 else -1 if margin < 0 else 0
    score = 1.0 if outcome > 0 else 0.0 if outcome < 0 else 0.5
    return outcome, score, margin, candidate_seat


def game_summary(rows: list[dict[str, Any]], candidate: str) -> dict[str, Any]:
    outcomes: list[int] = []
    scores: list[float] = []
    margins: list[float] = []
    for row in rows:
        outcome, score, margin, _ = candidate_values(row, candidate)
        outcomes.append(outcome)
        scores.append(score)
        margins.append(margin)
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
    win_values, dates = cluster_metric(
        grouped, candidate, lambda outcome, score, margin: float(outcome > 0)
    )
    score_values, _ = cluster_metric(grouped, candidate, lambda o, score, m: score)
    margin_values, _ = cluster_metric(grouped, candidate, lambda o, s, margin: margin)
    overall = game_summary(rows, candidate)
    overall.update(
        {
            "source_clusters": len(grouped),
            "pure_win_rate_ci95": bootstrap_ci(
                win_values, dates, f"{phase}:{candidate}:{anchor}:win"
            ),
            "competition_score_rate_ci95": bootstrap_ci(
                score_values, dates, f"{phase}:{candidate}:{anchor}:score"
            ),
            "mean_margin_ci95": bootstrap_ci(
                margin_values, dates, f"{phase}:{candidate}:{anchor}:margin"
            ),
        }
    )
    by_date: dict[str, Any] = {}
    for date in sorted(set(dates)):
        by_date[date] = game_summary(
            [row for row in rows if source_key(row["source"])[0] == date], candidate
        )
    by_seat: dict[str, Any] = {}
    for seat in (0, 1):
        by_seat[str(seat)] = game_summary(
            [row for row in rows if candidate_values(row, candidate)[3] == seat], candidate
        )
    return {"anchor": anchor, "overall": overall, "by_date": by_date, "by_candidate_seat": by_seat}


def audit(
    phase: str,
    candidate: str,
    games: Path,
    run_manifest_path: Path,
    registry_path: Path,
    r002: str,
    a2: str,
) -> dict[str, Any]:
    verify_report = verify()
    seal = json.loads((HERE / "protocol_seal.json").read_text(encoding="utf-8"))
    slate = load_slate()
    if candidate not in slate["candidate_order"]:
        raise ValueError("candidate is not in sealed slate")
    panel_path, panel, panel_records = load_panel(phase)
    contract = json.loads((HERE / "evaluation_contract.json").read_text(encoding="utf-8"))
    expected_sources = {source_key(row) for row in panel["records"]}
    registry = load_registry(registry_path.resolve())
    clean_registry_or_fail(registry_path.resolve(), registry, seal)
    anchors = [r002, a2]
    if anchors != [str(row["id"]) for row in slate["anchors"]]:
        raise ValueError("anchors differ from sealed slate")
    fingerprint = expected_run_fingerprint(
        phase, candidate, anchors, registry, panel_path, panel, panel_records
    )
    tasks = build_tasks(registry, candidate, anchors, panel_records, fingerprint)
    expected_by_id = {str(task["task_id"]): task for task in tasks}
    if len(expected_by_id) != len(tasks):
        raise ValueError("expected task IDs are not unique")
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    manifest_expectations = {
        "schema": "kaggriculture-v13-dual-anchor-run-1",
        "phase": phase,
        "candidate": candidate,
        "anchors": anchors,
        "run_fingerprint": fingerprint,
        "registry_file_sha256": file_sha256(registry_path),
        "registry_and_serving_code_sha256": seal["candidate_slate"][
            "clean_registry_and_code_sha256"
        ],
        "v10_evaluation_implementation_sha256": v10.implementation_fingerprint(),
        "evaluation_contract_file_sha256": file_sha256(HERE / "evaluation_contract.json"),
        "candidate_slate_file_sha256": file_sha256(HERE / "candidate_slate.json"),
        "candidate_slate_core_sha256": slate["slate_core_sha256"],
        "protocol_seal_file_sha256": file_sha256(HERE / "protocol_seal.json"),
        "panel_file_sha256": file_sha256(panel_path),
        "panel_records_sha256": panel["records_sha256"],
        "expected_games": len(tasks),
        "sources": len(panel_records),
        "targeted_pairs": [[candidate, anchor] for anchor in anchors],
        "confirmatory_execution_flag": phase == "confirmatory",
        "dry_run": False,
    }
    mismatched_manifest = {
        key: {"observed": run_manifest.get(key), "expected": value}
        for key, value in manifest_expectations.items()
        if run_manifest.get(key) != value
    }
    if mismatched_manifest:
        raise ValueError(f"run manifest differs from sealed task definition: {mismatched_manifest}")
    rows = read_jsonl(games)
    if candidate in {r002, a2} or r002 == a2:
        raise ValueError("candidate and anchors must be three distinct model IDs")
    allowed_pairs = {frozenset((candidate, r002)), frozenset((candidate, a2))}
    task_ids: set[str] = set()
    observed_task_ids: set[str] = set()
    grouped: dict[tuple[str, tuple[str, int, str, str]], list[dict[str, Any]]] = defaultdict(list)
    status_counts: Counter[str] = Counter()
    errors: list[dict[str, Any]] = []
    for row in rows:
        line = int(row["_physical_line"])
        task_id = str(row.get("task_id") or "")
        if not task_id or task_id in task_ids or task_id not in expected_by_id:
            raise ValueError(f"missing/duplicate task_id on line {line}: {task_id!r}")
        task_ids.add(task_id)
        validate_row_against_task(row, expected_by_id[task_id])
        observed_task_ids.add(task_id)
        pair = frozenset((str(row.get("model_a")), str(row.get("model_b"))))
        if pair not in allowed_pairs:
            raise ValueError(f"unexpected pair on line {line}: {sorted(pair)}")
        source = source_key(row.get("source") or {})
        if source not in expected_sources:
            raise ValueError(f"unknown source on line {line}: {source}")
        statuses = row.get("statuses")
        status_counts["/".join(str(value) for value in (statuses or []))] += 1
        row_error = row.get("error")
        rewards = row.get("rewards")
        if not isinstance(rewards, list) or len(rewards) != 2 or not all(
            finite_number(value) for value in rewards
        ):
            raise ValueError(f"invalid rewards on line {line}: {rewards!r}")
        if int(row.get("model_a_seat", -1)) not in {0, 1}:
            raise ValueError(f"invalid model_a_seat on line {line}")
        outcome, score, margin, seat = candidate_values(row, candidate)
        if not all(finite_number(value) for value in (score, margin)):
            raise ValueError(f"non-finite derived metric on line {line}")
        anchor = a2 if a2 in pair else r002
        grouped[(anchor, source)].append(row)
    if observed_task_ids != set(expected_by_id):
        missing = sorted(set(expected_by_id) - observed_task_ids)
        extra = sorted(observed_task_ids - set(expected_by_id))
        raise ValueError(f"exact task set closure failed: missing={missing[:3]} extra={extra[:3]}")
    expected_games = len(expected_sources) * 2 * 2
    if len(rows) != expected_games:
        raise ValueError(f"row closure failed: {len(rows)} != {expected_games}")
    for anchor in (r002, a2):
        for source in expected_sources:
            values = grouped.get((anchor, source), [])
            if len(values) != 2:
                raise ValueError(f"missing pair/seat closure: {anchor} {source} rows={len(values)}")
            seats = {candidate_values(row, candidate)[3] for row in values}
            if seats != {0, 1}:
                raise ValueError(f"unbalanced candidate seats: {anchor} {source} {seats}")
    by_anchor = {}
    for anchor in (r002, a2):
        anchor_rows = [
            row
            for row in rows
            if frozenset((str(row["model_a"]), str(row["model_b"])))
            == frozenset((candidate, anchor))
        ]
        by_anchor[anchor] = anchor_report(anchor_rows, candidate, anchor, phase)
    r002_overall = by_anchor[r002]["overall"]
    a2_overall = by_anchor[a2]["overall"]
    a2_worst_date = min(
        value["competition_score_rate"] for value in by_anchor[a2]["by_date"].values()
    )
    a2_worst_seat = min(
        value["competition_score_rate"]
        for value in by_anchor[a2]["by_candidate_seat"].values()
    )
    if phase == "screen":
        cfg = contract["screen_selection"]
        gates = {
            "integrity": True,
            "a2_score_point": a2_overall["competition_score_rate"]
            >= float(cfg["a2_competition_score_rate_min"]),
            "r002_score_point": r002_overall["competition_score_rate"]
            >= float(cfg["r002_competition_score_rate_min"]),
            "a2_worst_date": a2_worst_date
            >= float(cfg["a2_worst_date_competition_score_rate_min"]),
            "a2_worst_candidate_seat": a2_worst_seat
            >= float(cfg["a2_worst_candidate_seat_competition_score_rate_min"]),
        }
    else:
        cfg = contract["confirmatory_gate"]
        gates = {
            "integrity": True,
            "a2_score_point": a2_overall["competition_score_rate"]
            > float(cfg["a2_competition_score_rate_point_min_exclusive"]),
            "a2_score_ci95_low": a2_overall["competition_score_rate_ci95"][0]
            > float(cfg["a2_competition_score_rate_ci95_low_min_exclusive"]),
            "r002_score_point": r002_overall["competition_score_rate"]
            > float(cfg["r002_competition_score_rate_point_min_exclusive"]),
            "r002_score_ci95_low": r002_overall["competition_score_rate_ci95"][0]
            > float(cfg["r002_competition_score_rate_ci95_low_min_exclusive"]),
            "a2_worst_date": a2_worst_date
            >= float(cfg["worst_date_a2_competition_score_rate_min"]),
            "a2_worst_candidate_seat": a2_worst_seat
            >= float(cfg["worst_candidate_seat_a2_competition_score_rate_min"]),
        }
    return {
        "schema": "kaggriculture-v13-dual-anchor-audit-1",
        "phase": phase,
        "candidate": candidate,
        "anchors": [r002, a2],
        "panel": str(panel_path.resolve()),
        "panel_file_sha256": file_sha256(panel_path),
        "panel_records_sha256": panel["records_sha256"],
        "evaluation_contract_file_sha256": file_sha256(HERE / "evaluation_contract.json"),
        "protocol_verification": verify_report,
        "games": str(games.resolve()),
        "games_file_sha256": file_sha256(games),
        "run_manifest": str(run_manifest_path.resolve()),
        "run_manifest_file_sha256": file_sha256(run_manifest_path),
        "registry": str(registry_path.resolve()),
        "registry_file_sha256": file_sha256(registry_path),
        "run_fingerprint": fingerprint,
        "rows": len(rows),
        "expected_rows": expected_games,
        "source_clusters": len(expected_sources),
        "status_counts": dict(status_counts),
        "error_count": len(errors),
        "done_done_count": status_counts.get("DONE/DONE", 0),
        "by_anchor": by_anchor,
        "a2_worst_date_competition_score_rate": a2_worst_date,
        "a2_worst_candidate_seat_competition_score_rate": a2_worst_seat,
        "gates": gates,
        "passed": all(gates.values()),
        "metric_note": "pure win rate and competition score rate are intentionally separate",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("screen", "confirmatory"), required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--games", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument(
        "--registry", type=Path, default=HERE / "clean_screen_registry.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--r002", default="v12_incumbent_r002")
    parser.add_argument("--a2", default="v12a2_no_shop_gate")
    args = parser.parse_args()
    payload = audit(
        args.phase,
        args.candidate,
        args.games.resolve(),
        args.run_manifest.resolve(),
        args.registry.resolve(),
        args.r002,
        args.a2,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
