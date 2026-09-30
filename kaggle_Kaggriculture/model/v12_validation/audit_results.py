"""Read-only fail-closed auditor for the V12 targeted formal grid."""

from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from kaggle_Kaggriculture.model.v12_validation.protocol import (
    canonical,
    expected_tasks as build_expected_tasks,
    file_sha256,
    preflight,
    read_config,
    target_pairs,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as v10
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import load_registry


HERE = Path(__file__).resolve().parent


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line, object_pairs_hook=_unique_json_object)
            except json.JSONDecodeError as exc:
                raise ValueError(f"malformed JSONL at {path}:{line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"non-object JSONL row at {path}:{line_number}")
            row["_physical_line"] = line_number
            rows.append(row)
    return rows


def _source_key(source: Mapping[str, Any]) -> tuple[str, int, str, str]:
    split = str(source.get("split", "")).lower()
    if split == "val":
        split = "validation"
    return (
        str(source.get("date") or source.get("source_date") or "")[:10],
        int(source["seed"]),
        str(source.get("episode_id") or source.get("episodeId") or ""),
        split,
    )


def _stable_seed(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def _finite_json_number(value: Any) -> bool:
    """Accept only finite JSON numbers, never bools or numeric strings."""

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _bootstrap_ci(
    values: Iterable[float],
    label: str,
    strata: Iterable[str] | None = None,
    rounds: int = 10_000,
    alpha: float = 0.05,
) -> list[float | None]:
    """Date-stratified source-cluster bootstrap preserving date quotas."""

    array = np.asarray(list(values), dtype=np.float64)
    if not len(array):
        return [None, None]
    labels = list(strata) if strata is not None else ["all"] * len(array)
    if len(labels) != len(array):
        raise ValueError("bootstrap strata/value length mismatch")
    groups = [
        np.asarray([index for index, value in enumerate(labels) if value == label])
        for label in sorted(set(labels))
    ]
    rng = np.random.default_rng(_stable_seed(label))
    samples = np.empty(int(rounds), dtype=np.float64)
    for iteration in range(int(rounds)):
        indices = np.concatenate(
            [rng.choice(group, size=len(group), replace=True) for group in groups]
        )
        samples[iteration] = float(array[indices].mean())
    return [
        float(np.quantile(samples, alpha / 2.0)),
        float(np.quantile(samples, 1.0 - alpha / 2.0)),
    ]


def _model_score(row: Mapping[str, Any], model_id: str) -> float:
    score_a = float(row["score_a"])
    if row["model_a"] == model_id:
        return score_a
    if row["model_b"] == model_id:
        return 1.0 - score_a
    raise KeyError(model_id)


def _model_margin(row: Mapping[str, Any], model_id: str) -> float:
    margin_a = float(row["margin_a"])
    if row["model_a"] == model_id:
        return margin_a
    if row["model_b"] == model_id:
        return -margin_a
    raise KeyError(model_id)


def _paired_metric(
    rows_by_pair_source: Mapping[
        tuple[frozenset[str], tuple[str, int, str, str]], list[dict[str, Any]]
    ],
    model_id: str,
    opponent_id: str,
    source_key: tuple[str, int, str, str],
    metric: str,
) -> float:
    rows = rows_by_pair_source[(frozenset((model_id, opponent_id)), source_key)]
    if len(rows) != 2 or {int(row["model_a_seat"]) for row in rows} != {0, 1}:
        raise ValueError(
            f"missing balanced seats for {model_id} vs {opponent_id} at {source_key}"
        )
    function = _model_score if metric == "score" else _model_margin
    return float(np.mean([function(row, model_id) for row in rows]))


def _candidate_report(
    candidate: str,
    parent: str,
    opponents: list[str],
    sources: list[tuple[str, int, str, str]],
    rows_by_pair_source: Mapping[
        tuple[frozenset[str], tuple[str, int, str, str]], list[dict[str, Any]]
    ],
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    dates = [source[0] for source in sources]
    direct_scores = [
        _paired_metric(rows_by_pair_source, candidate, parent, source, "score")
        for source in sources
    ]
    direct_margins = [
        _paired_metric(rows_by_pair_source, candidate, parent, source, "margin")
        for source in sources
    ]
    common = [item for item in opponents if item not in {candidate, parent}]
    if not common:
        raise ValueError(f"no common opponents for {candidate} and {parent}")

    per_opponent: dict[str, Any] = {}
    source_score_deltas: dict[
        tuple[str, int, str, str], list[float]
    ] = defaultdict(list)
    source_margin_deltas: dict[
        tuple[str, int, str, str], list[float]
    ] = defaultdict(list)
    for opponent in common:
        score_deltas: list[float] = []
        margin_deltas: list[float] = []
        for source in sources:
            candidate_score = _paired_metric(
                rows_by_pair_source, candidate, opponent, source, "score"
            )
            parent_score = _paired_metric(
                rows_by_pair_source, parent, opponent, source, "score"
            )
            candidate_margin = _paired_metric(
                rows_by_pair_source, candidate, opponent, source, "margin"
            )
            parent_margin = _paired_metric(
                rows_by_pair_source, parent, opponent, source, "margin"
            )
            score_delta = candidate_score - parent_score
            margin_delta = candidate_margin - parent_margin
            score_deltas.append(score_delta)
            margin_deltas.append(margin_delta)
            source_score_deltas[source].append(score_delta)
            source_margin_deltas[source].append(margin_delta)
        score_ci = _bootstrap_ci(
            score_deltas, f"{candidate}:{parent}:{opponent}:score", dates
        )
        per_opponent[opponent] = {
            "paired_sources": len(score_deltas),
            "score_uplift": float(np.mean(score_deltas)),
            "score_uplift_ci95": score_ci,
            # A single opponent only has 100 source clusters.  Its interval is
            # diagnostic uncertainty, not a multiplicity-controlled gate; the
            # pre-registered per-opponent guardrail is the point estimate.
            "score_ci95_report_only": True,
            "margin_uplift": float(np.mean(margin_deltas)),
            "margin_uplift_ci95": _bootstrap_ci(
                margin_deltas, f"{candidate}:{parent}:{opponent}:margin", dates
            ),
        }

    aggregate_score = [
        float(np.mean(source_score_deltas[source])) for source in sources
    ]
    aggregate_margin = [
        float(np.mean(source_margin_deltas[source])) for source in sources
    ]
    direct_ci = _bootstrap_ci(
        direct_scores, f"{candidate}:{parent}:direct-score", dates
    )
    common_ci = _bootstrap_ci(
        aggregate_score, f"{candidate}:{parent}:common-score", dates
    )
    worst_point = min(
        float(value["score_uplift"]) for value in per_opponent.values()
    )
    worst_ci_low = min(
        float(value["score_uplift_ci95"][0]) for value in per_opponent.values()
    )
    gates = {
        "direct_parent_score_point": float(np.mean(direct_scores))
        >= float(thresholds["direct_parent_score_point_min"]),
        "direct_parent_score_ci95_low": float(direct_ci[0])
        >= float(thresholds["direct_parent_score_ci95_low_min"]),
        "common_opponent_uplift_point": float(np.mean(aggregate_score))
        > float(thresholds["common_opponent_uplift_point_min"]),
        "common_opponent_uplift_ci95_low": float(common_ci[0])
        > float(thresholds["common_opponent_uplift_ci95_low_min"]),
        "worst_common_opponent_point": worst_point
        >= float(thresholds["worst_common_opponent_point_min"]),
    }
    return {
        "candidate": candidate,
        "parent": parent,
        "direct_parent": {
            "paired_sources": len(direct_scores),
            "score_rate": float(np.mean(direct_scores)),
            "score_rate_ci95": direct_ci,
            "mean_margin": float(np.mean(direct_margins)),
            "mean_margin_ci95": _bootstrap_ci(
                direct_margins, f"{candidate}:{parent}:direct-margin", dates
            ),
        },
        "common_opponent_uplift": {
            "opponents": common,
            "paired_source_clusters": len(aggregate_score),
            "score_uplift": float(np.mean(aggregate_score)),
            "score_uplift_ci95": common_ci,
            "margin_uplift": float(np.mean(aggregate_margin)),
            "margin_uplift_ci95": _bootstrap_ci(
                aggregate_margin, f"{candidate}:{parent}:common-margin", dates
            ),
            "worst_opponent_score_uplift": worst_point,
            "worst_opponent_score_ci95_low": worst_ci_low,
            "per_opponent_ci_gate": False,
            "per_opponent": per_opponent,
        },
        "bootstrap": {
            "method": "source-cluster bootstrap stratified by date",
            "rounds": 10_000,
            "date_counts": dict(Counter(dates)),
        },
        "promotion_gates": gates,
        "promotion_qualified": all(gates.values()),
    }


def audit(config_path: Path, jsonl_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    jsonl_path = jsonl_path.expanduser().resolve()
    preflight_report = preflight(config_path)
    if preflight_report.get("passed") is not True:
        raise ValueError("formal audit preflight did not pass")
    config = read_config(config_path)
    registry = load_registry(config["combined_registry"])
    expected_fingerprint, task_manifest, evaluator_panel = build_expected_tasks(
        config, registry
    )
    expected_by_id = {str(task["task_id"]): task for task in task_manifest}
    expected_pairs = target_pairs(config)
    expected_pair_sets = {frozenset(pair) for pair in expected_pairs}
    sources = [_source_key(vars(item)) for item in evaluator_panel]
    source_set = set(sources)
    expected_grain = {
        (
            (str(task["model_a"]), str(task["model_b"])),
            _source_key(task["source"]),
            int(task["model_a_seat"]),
        )
        for task in task_manifest
    }

    rows = _read_jsonl(jsonl_path)
    task_ids = [str(row.get("task_id") or "") for row in rows]
    physical_grain: list[
        tuple[tuple[str, str], tuple[str, int, str, str], int]
    ] = []
    errors: list[dict[str, Any]] = []
    rows_by_pair_source: dict[
        tuple[frozenset[str], tuple[str, int, str, str]], list[dict[str, Any]]
    ] = defaultdict(list)

    for row in rows:
        try:
            task_value = expected_by_id.get(str(row.get("task_id") or ""))
            if task_value is None:
                raise ValueError("foreign or forged task_id")
            if row.get("schema") != v10.SCHEMA:
                raise ValueError("row schema mismatch")
            for key in (
                "run_fingerprint",
                "pair_id",
                "model_a",
                "model_b",
                "model_a_seat",
            ):
                if row.get(key) != task_value[key]:
                    raise ValueError(f"{key} mismatch")
            if canonical(dict(row.get("source") or {})) != canonical(
                dict(task_value["source"])
            ):
                raise ValueError("full source record mismatch")
            pair = (str(row["model_a"]), str(row["model_b"]))
            pair_set = frozenset(pair)
            source = _source_key(row["source"])
            if type(row.get("model_a_seat")) is not int:
                raise ValueError("model_a_seat must be an exact JSON integer")
            seat = int(row["model_a_seat"])
            physical_grain.append((pair, source, seat))
            if pair not in expected_pairs or pair_set not in expected_pair_sets:
                raise ValueError("pair orientation is not the registered order")
            if source not in source_set or seat not in {0, 1}:
                raise ValueError("foreign source/seat")
            expected_seats = [pair[0], pair[1]] if seat == 0 else [pair[1], pair[0]]
            if list(row.get("seat_models") or []) != expected_seats:
                raise ValueError("seat_models does not bind model_a_seat")
            if row.get("error") is not None:
                raise ValueError(f"row error: {row.get('error')}")
            if row.get("done") is not True or list(row.get("statuses") or []) != [
                "DONE",
                "DONE",
            ]:
                raise ValueError("non-DONE terminal state")
            if row.get("closed_loop") is not True or row.get("trace_agent") is not False:
                raise ValueError("not a closed-loop/no-trace result")
            if row.get("engine") != "kaggle_environments.make(kaggriculture)":
                raise ValueError("unexpected engine")
            rewards = list(row.get("rewards") or [])
            if len(rewards) != 2 or not all(
                _finite_json_number(value) for value in rewards
            ):
                raise ValueError("invalid rewards")
            reward_a = float(rewards[seat])
            reward_b = float(rewards[1 - seat])
            margin = reward_a - reward_b
            score = 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0
            for key in ("reward_a", "reward_b", "margin_a", "score_a"):
                if not _finite_json_number(row.get(key)):
                    raise ValueError(f"invalid {key}")
            # These values are all emitted from the same terminal reward pair;
            # tolerances would let a forged JSONL row alter the audit payload.
            if float(row["reward_a"]) != reward_a:
                raise ValueError("reward_a/seat mismatch")
            if float(row["reward_b"]) != reward_b:
                raise ValueError("reward_b/seat mismatch")
            if float(row["margin_a"]) != margin:
                raise ValueError("margin_a mismatch")
            if float(row["score_a"]) != score:
                raise ValueError("score_a mismatch")
            rows_by_pair_source[(pair_set, source)].append(row)
        except Exception as exc:
            errors.append(
                {
                    "physical_line": row.get("_physical_line"),
                    "task_id": row.get("task_id"),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    counter = Counter(physical_grain)
    checks = {
        "preflight_passed": preflight_report["passed"],
        "exact_targeted_physical_row_count": len(rows) == len(task_manifest) == 4600,
        "task_id_exact_unique_set": len(task_ids) == len(set(task_ids))
        and set(task_ids) == set(expected_by_id),
        "task_grain_exact_unique_set": len(physical_grain) == len(set(physical_grain))
        and set(physical_grain) == expected_grain,
        "exact_run_fingerprint": all(
            row.get("run_fingerprint") == expected_fingerprint for row in rows
        ),
        "zero_row_errors": not errors,
        "each_target_pair_100_sources_two_seats": all(
            counter[(pair, source, seat)] == 1
            for pair in expected_pairs
            for source in sources
            for seat in (0, 1)
        ),
        "common_panel_all_target_pairs": all(
            {
                source
                for (pair_key, source), pair_rows in rows_by_pair_source.items()
                if pair_key == frozenset(pair) and len(pair_rows) == 2
            }
            == source_set
            for pair in expected_pairs
        ),
    }
    integrity = all(checks.values())
    candidate_reports: list[dict[str, Any]] = []
    if integrity:
        for item in config["candidates"]:
            candidate_reports.append(
                _candidate_report(
                    str(item["id"]),
                    str(item["parent"]),
                    [str(value) for value in config["strong_opponents"]],
                    sources,
                    rows_by_pair_source,
                    config["quality_thresholds"],
                )
            )

    sequence = dict(config["fixed_sequence_gate"])
    reports_by_id = {item["candidate"]: item for item in candidate_reports}
    primary = reports_by_id.get(str(sequence["primary"]))
    secondary = reports_by_id.get(str(sequence["secondary"]))
    if primary is not None:
        primary["fixed_sequence_status"] = "primary_confirmatory_test"
        primary["fixed_sequence_qualified"] = primary["promotion_qualified"]
    primary_passed = bool(primary and primary["promotion_qualified"])
    if secondary is not None:
        secondary["fixed_sequence_status"] = (
            "secondary_confirmatory_interpretation"
            if primary_passed
            else "exploratory_only"
        )
        secondary["fixed_sequence_qualified"] = bool(
            primary_passed and secondary["promotion_qualified"]
        )

    return {
        "schema": "kaggriculture-v12-targeted-formal-audit-2",
        "read_only": True,
        "config": str(config_path),
        "config_file_sha256": file_sha256(config_path),
        "results_jsonl": str(jsonl_path),
        "results_jsonl_sha256": file_sha256(jsonl_path),
        "grain": "registered ordered pair x official source x fixed model_a seat",
        "preflight": preflight_report,
        "expected": {
            "models": len(config["formal_models"]),
            "targeted_pairs": len(expected_pairs),
            "sources_per_pair": len(sources),
            "seats_per_source": 2,
            "tasks": len(task_manifest),
            "run_fingerprint": expected_fingerprint,
        },
        "observed": {
            "physical_rows": len(rows),
            "unique_task_ids": len(set(task_ids)),
            "unique_task_grain": len(set(physical_grain)),
            "run_fingerprints": sorted(
                {str(row.get("run_fingerprint") or "") for row in rows}
            ),
        },
        "checks": checks,
        "integrity_passed": integrity,
        "integrity_errors": errors[:50],
        "candidate_parent_uplift": candidate_reports,
        "fixed_sequence": {
            **sequence,
            "primary_qualified": primary_passed,
            "secondary_formally_tested": primary_passed,
            "secondary_qualified": bool(
                secondary and secondary.get("fixed_sequence_qualified")
            ),
        },
        "any_fixed_sequence_candidate_qualified": bool(
            primary_passed
            or (secondary and secondary.get("fixed_sequence_qualified"))
        ),
        "interpretation": {
            "direct_parent": "candidate vs its own parent, paired over source and both seats",
            "common_opponent_uplift": "candidate minus parent against identical opponents/source/seats",
            "bootstrap": "10,000 source-cluster resamples within each date stratum",
            "multiplicity": "fixed sequence: incumbent r002 primary; A2 confirmatory only if the primary passes every gate, otherwise A2 is exploratory",
            "promotion_note": "no effect claim is computed until every integrity check passes",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=HERE / "frozen_v5" / "validation_config.json"
    )
    parser.add_argument(
        "--jsonl", type=Path, default=HERE / "runs_v5" / "formal" / "games.jsonl"
    )
    parser.add_argument(
        "--output", type=Path, default=HERE / "runs_v5" / "formal" / "audit.json"
    )
    args = parser.parse_args()
    report = audit(args.config, args.jsonl)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "integrity_passed": report["integrity_passed"],
                "any_fixed_sequence_candidate_qualified": report[
                    "any_fixed_sequence_candidate_qualified"
                ],
            },
            ensure_ascii=False,
        )
    )
    if not report["integrity_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
