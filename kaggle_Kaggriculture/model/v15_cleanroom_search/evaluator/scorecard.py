"""Strict V15 row audit and anonymous score-only aggregation."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from .protocol import (
    ALLOWED_SPLITS,
    BOOTSTRAP_ROUNDS,
    DATES,
    THRESHOLDS,
    canonical,
    finite_number,
    normalise_split,
    unique_json_loads,
)


GAME_SCHEMA = "kaggriculture-v10-pairwise-closed-loop-1"
GAME_ENGINE = "kaggle_environments.make(kaggriculture)"
TASK_BINDING_FIELDS = (
    "task_id",
    "run_fingerprint",
    "pair_id",
    "model_a",
    "model_b",
    "model_a_seat",
    "source",
)


PUBLIC_FIELDS = {
    "schema",
    "attempt_id",
    "integrity_passed",
    "primary_anchor_pure_win_rate",
    "secondary_anchor_pure_win_rate",
    "lineage_equal_pool_score_rate",
    "lineage_equal_pool_score_ci95_low",
    "paired_uplift_rate",
    "paired_uplift_ci95_low",
    "overall_passed",
}

FORBIDDEN_PUBLIC_KEY_PARTS = {
    "action",
    "date",
    "episode",
    "loss",
    "margin",
    "model_id",
    "opponent",
    "path",
    "reward",
    "row",
    "seed",
    "source",
    "submission",
    "tie",
}


def source_key(source: Mapping[str, Any]) -> tuple[str, int, str, str]:
    split = normalise_split(source.get("split"))
    if split not in ALLOWED_SPLITS or split == "test":
        raise PermissionError("test/unknown source split is forbidden")
    return (
        str(source.get("date") or "")[:10],
        int(source["seed"]),
        str(source.get("episode_id") or ""),
        split,
    )


def stable_seed(label: str) -> int:
    return int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:8], "big")


def stratified_cluster_ci_low(
    values: Mapping[tuple[str, int, str, str], float],
    label: str,
    rounds: int = BOOTSTRAP_ROUNDS,
) -> float:
    if not values:
        raise ValueError("cannot bootstrap an empty source-cluster mapping")
    by_date: dict[str, np.ndarray] = {}
    for date in sorted({key[0] for key in values}):
        array = np.asarray([value for key, value in values.items() if key[0] == date], dtype=np.float64)
        if not len(array):
            raise ValueError(f"empty date stratum: {date}")
        by_date[date] = array
    rng = np.random.default_rng(stable_seed(label))
    estimates = np.empty(int(rounds), dtype=np.float64)
    for index in range(int(rounds)):
        sampled = [rng.choice(array, size=len(array), replace=True) for array in by_date.values()]
        estimates[index] = float(np.concatenate(sampled).mean())
    return float(np.quantile(estimates, 0.025))


def _validate_row(
    row: Mapping[str, Any],
    *,
    expected_task: Mapping[str, Any],
    policy_ids: set[str],
    pool_ids: set[str],
    panel_sources: set[tuple[str, int, str, str]],
) -> tuple[str, str, int, tuple[str, int, str, str], float]:
    if row.get("schema") != GAME_SCHEMA:
        raise ValueError("unexpected raw-game schema")
    if row.get("engine") != GAME_ENGINE:
        raise ValueError("unexpected raw-game engine")
    for field in TASK_BINDING_FIELDS:
        # Canonical JSON comparison is intentional: Python considers True == 1,
        # but a sealed integer task may not be satisfied by a boolean row.
        if canonical(row.get(field)) != canonical(expected_task.get(field)):
            raise ValueError(f"raw row differs from sealed task field: {field}")
    policy = str(row.get("model_a") or "")
    opponent = str(row.get("model_b") or "")
    seat = row.get("model_a_seat")
    if policy not in policy_ids or opponent not in pool_ids:
        raise ValueError("foreign policy/pool identity in a raw row")
    if not isinstance(seat, int) or isinstance(seat, bool) or seat not in {0, 1}:
        raise ValueError("model_a_seat must be exactly 0 or 1")
    source = source_key(row.get("source") or {})
    if source not in panel_sources:
        raise ValueError("raw row contains a source outside the sealed panel")
    if row.get("closed_loop") is not True or row.get("trace_agent") is not False:
        raise ValueError("raw row is not a closed-loop non-trace game")
    if row.get("done") is not True or row.get("statuses") != ["DONE", "DONE"] or row.get("error") is not None:
        raise ValueError("raw row is not a clean DONE/DONE game")
    rewards = row.get("rewards")
    if not isinstance(rewards, list) or len(rewards) != 2 or not all(finite_number(value) for value in rewards):
        raise ValueError("invalid rewards in a raw row")
    expected_models = [policy, opponent] if seat == 0 else [opponent, policy]
    if row.get("seat_models") != expected_models:
        raise ValueError("seat_models differs from the sealed task")
    own = float(rewards[seat])
    other = float(rewards[1 - seat])
    for name, expected_value in (
        ("reward_a", own),
        ("reward_b", other),
        ("margin_a", own - other),
    ):
        value = row.get(name)
        if not finite_number(value) or float(value) != expected_value:
            raise ValueError(f"derived {name} mismatch")
    score = 1.0 if own > other else 0.5 if own == other else 0.0
    if not finite_number(row.get("score_a")) or float(row["score_a"]) != score:
        raise ValueError("derived score_a mismatch")
    return policy, opponent, int(seat), source, score


def validate_task_subset(
    rows: Iterable[Mapping[str, Any]],
    *,
    expected_tasks: Mapping[str, Mapping[str, Any]],
    policy_ids: set[str],
    pool_ids: set[str],
    panel_records: Iterable[Mapping[str, Any]],
) -> set[str]:
    """Validate an existing JSONL as a clean, duplicate-free task subset.

    This is deliberately stricter than the V10 convenience resume behaviour:
    failed, incomplete, foreign, repeated, or semantically inconsistent rows
    cannot be used as a V15 resume prefix.
    """

    panel_sources = {source_key(row) for row in panel_records}
    task_ids: set[str] = set()
    logical_keys: set[tuple[str, str, int, tuple[str, int, str, str]]] = set()
    for row in rows:
        task_id = row.get("task_id")
        if not isinstance(task_id, str) or not task_id or task_id in task_ids:
            raise ValueError("missing or duplicate task id")
        expected = expected_tasks.get(task_id)
        if expected is None:
            raise ValueError("raw row contains a foreign task id")
        policy, opponent, seat, source, _ = _validate_row(
            row,
            expected_task=expected,
            policy_ids=policy_ids,
            pool_ids=pool_ids,
            panel_sources=panel_sources,
        )
        logical = (policy, opponent, seat, source)
        if logical in logical_keys:
            raise ValueError("duplicate policy/opponent/seat/source row")
        task_ids.add(task_id)
        logical_keys.add(logical)
    return task_ids


def audit_and_score(
    rows: list[dict[str, Any]],
    *,
    attempt_id: str,
    candidate_id: str,
    parent_id: str,
    panel_records: Iterable[Mapping[str, Any]],
    pool_to_lineage: Mapping[str, str],
    expected_tasks: Mapping[str, Mapping[str, Any]],
    primary_anchor_id: str,
    secondary_anchor_id: str,
    integrity_passed: bool,
    bootstrap_label: str,
    rounds: int = BOOTSTRAP_ROUNDS,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if candidate_id == parent_id:
        raise ValueError("candidate and parent identities must differ")
    if not pool_to_lineage:
        raise ValueError("formal pool cannot be empty")
    pool_ids = set(pool_to_lineage)
    if primary_anchor_id not in pool_ids or secondary_anchor_id not in pool_ids:
        raise ValueError("both direct anchors must be part of the evaluated pool")
    panel_records = list(panel_records)
    panel_sources = {source_key(row) for row in panel_records}
    if len(panel_sources) != 100:
        raise ValueError("formal panel must contain exactly 100 unique source clusters")
    if {source[0] for source in panel_sources} != set(DATES):
        raise ValueError("formal panel must cover exactly the frozen 2026-08-18..20 dates")

    expected_keys = {
        (policy, opponent, seat, source)
        for policy in (candidate_id, parent_id)
        for opponent in pool_ids
        for seat in (0, 1)
        for source in panel_sources
    }
    if len(expected_tasks) != len(expected_keys):
        raise ValueError("sealed expected-task count differs from logical closure")
    expected_logical: set[tuple[str, str, int, tuple[str, int, str, str]]] = set()
    for task_id, task in expected_tasks.items():
        if not isinstance(task_id, str) or task.get("task_id") != task_id:
            raise ValueError("expected-task index is malformed")
        try:
            logical = (
                str(task["model_a"]),
                str(task["model_b"]),
                int(task["model_a_seat"]),
                source_key(task["source"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("expected task is malformed") from exc
        expected_logical.add(logical)
    if expected_logical != expected_keys:
        raise ValueError("sealed expected tasks differ from logical closure")

    observed: dict[tuple[str, str, int, tuple[str, int, str, str]], float] = {}
    task_ids = validate_task_subset(
        rows,
        expected_tasks=expected_tasks,
        policy_ids={candidate_id, parent_id},
        pool_ids=pool_ids,
        panel_records=panel_records,
    )
    for row in rows:
        task_id = str(row["task_id"])
        policy, opponent, seat, source, score = _validate_row(
            row,
            expected_task=expected_tasks[task_id],
            policy_ids={candidate_id, parent_id},
            pool_ids=pool_ids,
            panel_sources=panel_sources,
        )
        key = (policy, opponent, seat, source)
        observed[key] = score
    if set(observed) != expected_keys:
        raise ValueError(
            f"exact task closure failed: observed={len(observed)} expected={len(expected_keys)}"
        )

    candidate_by_source: dict[tuple[str, int, str, str], float] = {}
    parent_by_source: dict[tuple[str, int, str, str], float] = {}
    uplift_by_source: dict[tuple[str, int, str, str], float] = {}
    lineage_groups: dict[str, list[str]] = defaultdict(list)
    for pool_id, lineage in pool_to_lineage.items():
        if not isinstance(lineage, str) or not lineage:
            raise ValueError("pool lineage names must be non-empty strings")
        lineage_groups[lineage].append(pool_id)

    for source in sorted(panel_sources):
        candidate_lineage_values: list[float] = []
        parent_lineage_values: list[float] = []
        for lineage in sorted(lineage_groups):
            candidate_models: list[float] = []
            parent_models: list[float] = []
            for pool_id in sorted(lineage_groups[lineage]):
                candidate_models.append(float(np.mean([
                    observed[(candidate_id, pool_id, seat, source)] for seat in (0, 1)
                ])))
                parent_models.append(float(np.mean([
                    observed[(parent_id, pool_id, seat, source)] for seat in (0, 1)
                ])))
            candidate_lineage_values.append(float(np.mean(candidate_models)))
            parent_lineage_values.append(float(np.mean(parent_models)))
        candidate_by_source[source] = float(np.mean(candidate_lineage_values))
        parent_by_source[source] = float(np.mean(parent_lineage_values))
        uplift_by_source[source] = candidate_by_source[source] - parent_by_source[source]

    def anchor_win_rate(anchor: str) -> float:
        values = [
            observed[(candidate_id, anchor, seat, source)]
            for source in panel_sources
            for seat in (0, 1)
        ]
        if len(values) != 200:
            raise ValueError("direct anchor closure is not 200 games")
        return float(np.mean([value == 1.0 for value in values]))

    primary = anchor_win_rate(primary_anchor_id)
    secondary = anchor_win_rate(secondary_anchor_id)
    pool_score = float(np.mean(list(candidate_by_source.values())))
    paired_uplift = float(np.mean(list(uplift_by_source.values())))
    pool_ci_low = stratified_cluster_ci_low(
        candidate_by_source, f"{bootstrap_label}:pool-score", rounds=rounds
    )
    uplift_ci_low = stratified_cluster_ci_low(
        uplift_by_source, f"{bootstrap_label}:paired-uplift", rounds=rounds
    )
    passed = bool(
        integrity_passed
        and primary >= THRESHOLDS["primary_anchor_pure_win_rate_min"]
        and pool_score >= THRESHOLDS["lineage_equal_pool_score_rate_min"]
        and pool_ci_low >= THRESHOLDS["lineage_equal_pool_score_ci95_low_min"]
        and uplift_ci_low > THRESHOLDS["paired_uplift_ci95_low_strict_min"]
    )
    feedback = {
        "schema": "kaggriculture-v15-score-only-feedback-v1",
        "attempt_id": attempt_id,
        "integrity_passed": bool(integrity_passed),
        "primary_anchor_pure_win_rate": primary,
        "secondary_anchor_pure_win_rate": secondary,
        "lineage_equal_pool_score_rate": pool_score,
        "lineage_equal_pool_score_ci95_low": pool_ci_low,
        "paired_uplift_rate": paired_uplift,
        "paired_uplift_ci95_low": uplift_ci_low,
        "overall_passed": passed,
    }
    validate_public_feedback(feedback)
    private = {
        "schema": "kaggriculture-v15-private-score-audit-1",
        "attempt_id": attempt_id,
        "raw_rows": len(rows),
        "source_clusters": len(panel_sources),
        "models_evaluated": len(pool_to_lineage),
        "behaviour_lineages_equal_weighted": len(lineage_groups),
        "games_per_direct_anchor": 200,
        "paired_key": "same source, candidate seat, and frozen opponent",
        "source_cluster_definition": (
            "two seats averaged within model; models averaged within lineage; "
            "lineages equally averaged"
        ),
        "bootstrap": {
            "unit": "source cluster",
            "date_stratified": True,
            "rounds": int(rounds),
            "quantile": 0.025,
        },
        "thresholds": THRESHOLDS,
        "feedback": feedback,
        "task_ids_sha256": hashlib.sha256(canonical(sorted(task_ids))).hexdigest(),
    }
    return feedback, private


def validate_public_feedback(payload: Mapping[str, Any]) -> None:
    if set(payload) != PUBLIC_FIELDS:
        raise ValueError(f"score-only fields differ from contract: {sorted(set(payload) ^ PUBLIC_FIELDS)}")
    if payload.get("schema") != "kaggriculture-v15-score-only-feedback-v1":
        raise ValueError("unexpected score-only schema")
    if not isinstance(payload.get("attempt_id"), str):
        raise ValueError("score-only attempt_id must be a string")
    for key, value in payload.items():
        lowered = key.lower()
        if any(part in lowered for part in FORBIDDEN_PUBLIC_KEY_PARTS):
            raise ValueError(f"forbidden detail leaked through score-only key: {key}")
        if key.endswith("_rate") or key.endswith("_low"):
            if not finite_number(value) or not -1.0 <= float(value) <= 1.0:
                raise ValueError(f"invalid aggregate rate: {key}")
    for key in ("integrity_passed", "overall_passed"):
        if not isinstance(payload.get(key), bool):
            raise ValueError(f"{key} must be boolean")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = unique_json_loads(line, source=f"{path}:{line_number}")
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"malformed JSONL at line {line_number}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"non-object JSONL row at line {line_number}")
            rows.append(value)
    return rows
