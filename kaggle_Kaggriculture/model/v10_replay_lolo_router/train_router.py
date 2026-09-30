"""Train and audit the V10 public-state learned Router.

Input is the closed-loop potential-outcome grid emitted by
``collect_router_grid.py``.
Training uses only manifest ``train``/``validation`` rows; ``test`` is frozen
and is touched only by the final policy comparison.  LOLO means holding out an
entire opponent *root* production lineage (V1/V2/V5/V8), including all its
variants.  All candidate experts remain available in every fold, so the fold
tests opponent-lineage generalisation without silently changing the Router's
action space.

The learned model is deliberately small: an independently ridge-regularised
linear expected-score head for every complete expert.  The exported NPZ is
NumPy-only and is consumed directly by ``router.LearnedSelector``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

try:
    from .agent_factory import Registry, load_registry, registry_fingerprint
    from .collect_router_grid import implementation_fingerprint as grid_implementation_fingerprint
    from .router import FEATURE_DIM, FEATURE_NAMES, FEATURE_SCHEMA, ROUTER_WEIGHT_SCHEMA, RuleSelector
except ImportError:  # direct-script compatibility
    from agent_factory import Registry, load_registry, registry_fingerprint
    from collect_router_grid import implementation_fingerprint as grid_implementation_fingerprint
    from router import FEATURE_DIM, FEATURE_NAMES, FEATURE_SCHEMA, ROUTER_WEIGHT_SCHEMA, RuleSelector


SCHEMA = "kaggriculture-v10-learned-router-training-1"
GRID_SCHEMA = "kaggriculture-v10-router-outcome-grid-1"


def training_implementation_fingerprint() -> str:
    payload = {
        "python": list(sys.version_info[:2]),
        "numpy": np.__version__,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    digest.update(Path(__file__).resolve().read_bytes())
    return digest.hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class Perspective:
    date: str
    episode_id: str
    seed: int
    split: str
    seat: int
    model_id: str
    opponent_id: str
    model_lineage: str
    opponent_lineage: str
    score: float
    margin: float
    features: np.ndarray
    feature_hash: str


class LoadedRows(list[dict[str, Any]]):
    """JSONL rows plus a deterministic resume/deduplication audit."""

    def __init__(self, values: Iterable[dict[str, Any]], audit: Mapping[str, Any]):
        super().__init__(values)
        self.audit = dict(audit)


def _root_lineage(value: Any, fallback: str) -> str:
    if isinstance(value, (list, tuple)) and value:
        return str(value[0])
    text = str(value or fallback)
    # JSON-serialised tuples from ad-hoc registries are uncommon but easy to
    # normalise conservatively by using the first non-empty token.
    return text


def _successful(row: Mapping[str, Any]) -> bool:
    return row.get("error") is None and row.get("done") is True


def _result_digest(row: Mapping[str, Any]) -> str:
    """Hash result semantics while ignoring harmless timing/append metadata."""

    import hashlib

    keys = (
        "schema", "task_id", "collection_fingerprint", "run_fingerprint",
        "candidate", "opponent", "router_seat", "source", "prefix_complete",
        "prefix_match", "switch_feature_sha256", "switch_features",
        "candidate_score", "candidate_margin", "model_a", "model_b",
        "model_a_seat", "score_a", "margin_a",
    )
    payload = {key: row.get(key) for key in keys if key in row}
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_jsonl(paths: Sequence[Path]) -> LoadedRows:
    rows_by_task: dict[str, dict[str, Any]] = {}
    audit = Counter()
    for path in paths:
        with path.expanduser().resolve().open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                audit["input_records"] += 1
                task_id = str(row.get("task_id") or f"{path}:{line_number}")
                previous = rows_by_task.get(task_id)
                success = _successful(row)
                previous_success = previous is not None and _successful(previous)
                if previous is not None:
                    audit["duplicate_records"] += 1
                if success and previous_success:
                    if _result_digest(row) != _result_digest(previous):
                        audit["conflicting_success_records"] += 1
                    else:
                        audit["identical_success_records"] += 1
                elif success and previous is not None:
                    audit["retry_success_replacements"] += 1
                elif previous_success:
                    audit["failure_after_success_ignored"] += 1
                # A retry success supersedes an earlier error.  Multiple
                # successful duplicates are deterministic; keep the latest so
                # an interrupted append can be resumed without preserving a
                # stale first row forever.
                if previous is None or success or not previous_success:
                    rows_by_task[task_id] = row
    audit["unique_tasks"] = len(rows_by_task)
    return LoadedRows(rows_by_task.values(), dict(audit))


def _normalise_split(value: Any) -> str:
    value = str(value or "").lower()
    return "validation" if value == "val" else value


def perspectives(rows: Sequence[Mapping[str, Any]], registry: Registry) -> list[Perspective]:
    result: list[Perspective] = []
    for row in rows:
        if row.get("error") is not None or not row.get("done") or row.get("score_a") is None:
            if row.get("schema") != GRID_SCHEMA or row.get("candidate_score") is None:
                continue
        if row.get("schema") == GRID_SCHEMA:
            model_id, opponent_id = str(row["candidate"]), str(row["opponent"])
            if model_id not in registry.models or opponent_id not in registry.models:
                continue
            vector = np.asarray(row.get("switch_features"), dtype=np.float32)
            if vector.shape != (FEATURE_DIM,) or not np.all(np.isfinite(vector)):
                continue
            source = row.get("source") or {}
            expected_model_lineage = _root_lineage(
                registry.require(model_id).get("lineage"), model_id
            )
            expected_opponent_lineage = _root_lineage(
                registry.require(opponent_id).get("lineage"), opponent_id
            )
            if not row.get("candidate_root_lineage") or not row.get("opponent_root_lineage"):
                raise ValueError("router grid is missing curated root-lineage labels")
            reported_model_lineage = str(row["candidate_root_lineage"])
            reported_opponent_lineage = str(row["opponent_root_lineage"])
            if (
                reported_model_lineage != expected_model_lineage
                or reported_opponent_lineage != expected_opponent_lineage
            ):
                raise ValueError(
                    "router grid root-lineage labels disagree with current registry"
                )
            result.append(Perspective(
                date=str(source.get("date") or ""),
                episode_id=str(source.get("episode_id") or ""),
                seed=int(source.get("seed") or 0),
                split=_normalise_split(source.get("split")),
                seat=int(row.get("router_seat") or 0),
                model_id=model_id,
                opponent_id=opponent_id,
                model_lineage=expected_model_lineage,
                opponent_lineage=expected_opponent_lineage,
                score=float(row["candidate_score"]),
                margin=float(row["candidate_margin"]),
                features=vector,
                feature_hash=str(row.get("switch_feature_sha256") or ""),
            ))
            continue
        source = row.get("source") or {}
        diagnostics = row.get("agent_diagnostics") or {}
        seat_diagnostics = row.get("seat_diagnostics") or []
        model_a, model_b = str(row["model_a"]), str(row["model_b"])
        a_seat = int(row["model_a_seat"])
        score_a = float(row["score_a"])
        margin_a = float(row["margin_a"])
        for model_id, opponent_id, seat, score, margin in (
            (model_a, model_b, a_seat, score_a, margin_a),
            (model_b, model_a, 1 - a_seat, 1.0 - score_a, -margin_a),
        ):
            if model_id not in registry.models or opponent_id not in registry.models:
                continue
            diag = (
                seat_diagnostics[seat]
                if len(seat_diagnostics) == 2 and isinstance(seat_diagnostics[seat], Mapping)
                else diagnostics.get(model_id) or {}
            )
            vector = np.asarray(diag.get("switch_features"), dtype=np.float32)
            if vector.shape != (FEATURE_DIM,) or not np.all(np.isfinite(vector)):
                continue
            model_spec, opponent_spec = registry.require(model_id), registry.require(opponent_id)
            result.append(Perspective(
                date=str(source.get("date") or ""),
                episode_id=str(source.get("episode_id") or ""),
                seed=int(source.get("seed") or 0),
                split=_normalise_split(source.get("split")),
                seat=seat,
                model_id=model_id,
                opponent_id=opponent_id,
                model_lineage=_root_lineage(model_spec.get("lineage"), model_id),
                opponent_lineage=_root_lineage(opponent_spec.get("lineage"), opponent_id),
                score=score,
                margin=margin,
                features=vector,
                feature_hash=str(diag.get("switch_feature_hash") or ""),
            ))
    return result


@dataclass
class LinearHeads:
    classes: tuple[str, ...]
    mean: np.ndarray
    scale: np.ndarray
    coef: np.ndarray
    intercept: np.ndarray
    support: dict[str, int]

    def scores(self, vector: Sequence[float]) -> dict[str, float]:
        x = np.asarray(vector, dtype=np.float32)
        x = np.clip((x - self.mean) / self.scale, -8.0, 8.0)
        values = x @ self.coef + self.intercept
        return {name: float(values[index]) for index, name in enumerate(self.classes)}

    def choose(self, vector: Sequence[float], eligible: Sequence[str]) -> str:
        scores = self.scores(vector)
        valid = [(scores[item], -index, item) for index, item in enumerate(eligible) if item in scores]
        if not valid:
            raise ValueError("no eligible trained class")
        return max(valid)[2]


def fit_heads(rows: Sequence[Perspective], classes: Sequence[str], ridge: float, min_support: int) -> LinearHeads:
    classes = tuple(str(item) for item in classes)
    selected = [row for row in rows if row.model_id in classes]
    if not selected:
        raise ValueError("no training perspectives for requested experts")
    matrix = np.stack([row.features for row in selected]).astype(np.float64)
    mean = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale = np.where(scale < 1e-6, 1.0, scale)
    coef = np.zeros((FEATURE_DIM, len(classes)), dtype=np.float64)
    intercept = np.zeros(len(classes), dtype=np.float64)
    support: dict[str, int] = {}
    for column, model_id in enumerate(classes):
        examples = [row for row in selected if row.model_id == model_id]
        support[model_id] = len(examples)
        if len(examples) < int(min_support):
            raise ValueError(f"insufficient training support for {model_id}: {len(examples)} < {min_support}")
        x = np.stack([row.features for row in examples]).astype(np.float64)
        x = np.clip((x - mean) / scale, -8.0, 8.0)
        x = np.column_stack([x, np.ones(len(x), dtype=np.float64)])
        y = np.asarray([row.score for row in examples], dtype=np.float64)
        penalty = np.eye(x.shape[1], dtype=np.float64) * float(ridge)
        penalty[-1, -1] = 0.0
        beta = np.linalg.solve(x.T @ x + penalty, x.T @ y)
        coef[:, column], intercept[column] = beta[:-1], beta[-1]
    return LinearHeads(
        classes=classes,
        mean=mean.astype(np.float32), scale=scale.astype(np.float32),
        coef=coef.astype(np.float32), intercept=intercept.astype(np.float32), support=support,
    )


def save_weights(model: LinearHeads, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        schema=np.asarray(ROUTER_WEIGHT_SCHEMA),
        feature_schema=np.asarray(FEATURE_SCHEMA),
        feature_names=np.asarray(FEATURE_NAMES),
        classes=np.asarray(model.classes),
        mean=model.mean,
        scale=model.scale,
        coef=model.coef,
        intercept=model.intercept,
    )


def _training_rank(rows: Sequence[Perspective], classes: Sequence[str]) -> list[str]:
    by_model: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row.model_id in classes:
            by_model[row.model_id].append(row.score)
    return sorted(classes, key=lambda item: (float(np.mean(by_model[item])) if by_model[item] else -1.0, item), reverse=True)


def _contexts(
    rows: Sequence[Perspective], candidate_ids: set[str], opponent_lineage: str | None = None
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    grouped: dict[tuple[Any, ...], dict[str, Perspective]] = defaultdict(dict)
    for row in rows:
        if row.model_id not in candidate_ids:
            continue
        if opponent_lineage is not None and row.opponent_lineage != opponent_lineage:
            continue
        key = (row.date, row.episode_id, row.seed, row.seat, row.opponent_id)
        grouped[key][row.model_id] = row
    contexts = []
    rejected = Counter()
    for key, outcomes in grouped.items():
        if set(outcomes) != candidate_ids:
            rejected["incomplete_candidate_grid"] += 1
            continue
        if any(not row.feature_hash for row in outcomes.values()):
            rejected["missing_step72_feature_hash"] += 1
            continue
        hashes = {row.feature_hash for row in outcomes.values()}
        if len(hashes) > 1:
            rejected["inconsistent_step72_state"] += 1
            continue
        anchor = sorted(outcomes)[0]
        contexts.append({
            "key": key,
            "opponent_lineage": next(iter(outcomes.values())).opponent_lineage,
            "features": outcomes[anchor].features,
            "outcomes": outcomes,
            "feature_hash_consistent": len(hashes) <= 1,
        })
    return contexts, dict(rejected)


def _bootstrap_difference(values: Sequence[float], seed: int, rounds: int = 4000) -> list[float | None]:
    array = np.asarray(values, dtype=np.float64)
    if not len(array):
        return [None, None]
    rng = np.random.default_rng(seed)
    samples = np.empty(rounds, dtype=np.float64)
    for start in range(0, rounds, 500):
        count = min(500, rounds - start)
        indices = rng.integers(0, len(array), size=(count, len(array)))
        samples[start:start + count] = array[indices].mean(axis=1)
    return [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]


def _clustered_differences(
    rows: Sequence[Mapping[str, Any]], left: str, right: str, metric: str = "scores"
) -> list[float]:
    """Collapse opponent/seat contexts to independent official seed clusters."""
    clusters: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for row in rows:
        context = row["context"]
        key = (str(context[0]), str(context[1]), int(context[2]))
        clusters[key].append(float(row[metric][left]) - float(row[metric][right]))
    return [float(np.mean(values)) for values in clusters.values()]


def _clustered_policy_values(
    rows: Sequence[Mapping[str, Any]], policy: str, metric: str
) -> list[float]:
    clusters: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for row in rows:
        context = row["context"]
        key = (str(context[0]), str(context[1]), int(context[2]))
        clusters[key].append(float(row[metric][policy]))
    return [float(np.mean(values)) for values in clusters.values()]


def evaluate_policies(
    rows: Sequence[Perspective],
    classes: Sequence[str],
    model: LinearHeads,
    fixed_rank: Sequence[str],
    rule_selector: RuleSelector,
    opponent_lineage: str | None,
) -> dict[str, Any]:
    contexts, rejected = _contexts(rows, set(classes), opponent_lineage)
    scores = {"best_fixed": [], "rule_router": [], "learned_router": [], "oracle": []}
    margins = {"best_fixed": [], "rule_router": [], "learned_router": [], "oracle": []}
    selections = {"best_fixed": Counter(), "rule_router": Counter(), "learned_router": Counter()}
    rule_reasons = Counter()
    rows_out = []
    for context in contexts:
        outcomes: dict[str, Perspective] = context["outcomes"]
        eligible = [item for item in classes if item in outcomes]
        if len(eligible) < 2:
            continue
        fixed = next(item for item in fixed_rank if item in eligible)
        rule = rule_selector.choose_vector(context["features"], eligible)
        rule_reason = str(rule_selector.last_reason)
        rule_reasons[rule_reason] += 1
        learned = model.choose(context["features"], eligible)
        oracle = max(eligible, key=lambda item: (outcomes[item].score, outcomes[item].margin, item))
        chosen = {"best_fixed": fixed, "rule_router": rule, "learned_router": learned, "oracle": oracle}
        for policy, model_id in chosen.items():
            scores[policy].append(outcomes[model_id].score)
            margins[policy].append(outcomes[model_id].margin)
            if policy in selections:
                selections[policy][model_id] += 1
        rows_out.append({
            "context": list(context["key"]), "eligible": eligible,
            "feature_hash_consistent": context["feature_hash_consistent"],
            "selected": chosen,
            "rule_reason": rule_reason,
            "scores": {key: outcomes[value].score for key, value in chosen.items()},
            "margins": {key: outcomes[value].margin for key, value in chosen.items()},
        })
    learned_minus_fixed = _clustered_differences(rows_out, "learned_router", "best_fixed")
    learned_minus_rule = _clustered_differences(rows_out, "learned_router", "rule_router")
    learned_margin_minus_fixed = _clustered_differences(
        rows_out, "learned_router", "best_fixed", "margins"
    )
    learned_margin_minus_rule = _clustered_differences(
        rows_out, "learned_router", "rule_router", "margins"
    )
    reason_total = sum(rule_reasons.values())
    policy_metrics = {}
    for index, policy in enumerate(scores):
        score_clusters = _clustered_policy_values(rows_out, policy, "scores")
        margin_clusters = _clustered_policy_values(rows_out, policy, "margins")
        policy_metrics[policy] = {
            "score_rate": float(np.mean(score_clusters)) if score_clusters else None,
            "score_ci95": _bootstrap_difference(score_clusters, 1801 + index),
            "mean_margin": float(np.mean(margin_clusters)) if margin_clusters else None,
            "margin_ci95": _bootstrap_difference(margin_clusters, 1901 + index),
        }
    return {
        "contexts": len(rows_out),
        "independent_seed_clusters": len({(row["context"][0], row["context"][1], row["context"][2]) for row in rows_out}),
        "rejected_contexts": rejected,
        "feature_hash_consistency_rate": 1.0 if rows_out else None,
        "score_rate": {key: (float(np.mean(value)) if value else None) for key, value in scores.items()},
        "mean_margin": {key: (float(np.mean(value)) if value else None) for key, value in margins.items()},
        "policy_metrics": policy_metrics,
        "selection_counts": {key: dict(value) for key, value in selections.items()},
        "selection_rates": {
            key: {
                model_id: count / max(1, sum(values.values()))
                for model_id, count in values.items()
            }
            for key, values in selections.items()
        },
        "rule_reason_counts": dict(rule_reasons),
        "rule_reason_max_share": (max(rule_reasons.values()) / reason_total) if reason_total else None,
        "learned_minus_fixed": float(np.mean(learned_minus_fixed)) if learned_minus_fixed else None,
        "learned_minus_fixed_ci95": _bootstrap_difference(learned_minus_fixed, 1729),
        "learned_minus_rule": float(np.mean(learned_minus_rule)) if learned_minus_rule else None,
        "learned_minus_rule_ci95": _bootstrap_difference(learned_minus_rule, 1733),
        "learned_margin_minus_fixed": (
            float(np.mean(learned_margin_minus_fixed)) if learned_margin_minus_fixed else None
        ),
        "learned_margin_minus_fixed_ci95": _bootstrap_difference(
            learned_margin_minus_fixed, 1741
        ),
        "learned_margin_minus_rule": (
            float(np.mean(learned_margin_minus_rule)) if learned_margin_minus_rule else None
        ),
        "learned_margin_minus_rule_ci95": _bootstrap_difference(
            learned_margin_minus_rule, 1747
        ),
        "rows": rows_out,
    }


def _root_lineages(registry: Registry, classes: Sequence[str]) -> dict[str, str]:
    return {model_id: _root_lineage(registry.require(model_id).get("lineage"), model_id) for model_id in classes}


def default_rule_spec(classes: Sequence[str]) -> dict[str, Any]:
    """Frozen public-state rule Router used for validation and final serving."""

    ordered = [str(item) for item in classes]

    def priority(preferred: str) -> list[str]:
        matches = [item for item in ordered if preferred in item]
        return list(dict.fromkeys([*matches, *ordered]))

    return {
        "id": "rule_router",
        "rule": {
            # A near-zero bank is normal after the shared opening and must not
            # collapse every sample into the survival branch.
            "low_cash": 0,
            "novelty_distance": 4.0,
            "default_priority": priority("v5"),
            "yarn_priority": priority("v8"),
            "novel_priority": priority("v1"),
            "survival_priority": priority("v2"),
        },
    }


def formal_grid_audit(
    rows: Sequence[Mapping[str, Any]],
    classes: Sequence[str],
    input_audit: Mapping[str, Any],
) -> dict[str, Any]:
    """Check the preregistered 100+100, four-by-four potential-outcome grid."""

    classes = tuple(str(item) for item in classes)
    expected_classes = (
        "baseline_v1", "baseline_v2", "baseline_v5", "baseline_v8"
    )
    by_split = Counter()
    sources: dict[str, set[tuple[str, str, int]]] = defaultdict(set)
    contexts: dict[tuple[Any, ...], set[str]] = defaultdict(set)
    opponents: dict[str, set[str]] = defaultdict(set)
    dates: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        source = row.get("source") or {}
        split = _normalise_split(source.get("split"))
        source_key = (
            str(source.get("date") or ""),
            str(source.get("episode_id") or ""),
            int(source.get("seed") or 0),
        )
        by_split[split] += 1
        sources[split].add(source_key)
        dates[split][source_key[0]] += 1
        opponent = str(row.get("opponent") or "")
        opponents[split].add(opponent)
        context_key = (*source_key, int(row.get("router_seat") or 0), opponent)
        contexts[(split, *context_key)].add(str(row.get("candidate") or ""))

    context_counts = Counter(key[0] for key in contexts)
    incomplete = {
        str(key): sorted(value)
        for key, value in contexts.items()
        if value != set(classes)
    }
    source_overlap = sources.get("train", set()) & sources.get("validation", set())
    expected_date_sources = {
        "2026-08-18": 34,
        "2026-08-19": 33,
        "2026-08-20": 33,
    }
    source_date_counts = {
        split: dict(Counter(source[0] for source in values))
        for split, values in sources.items()
    }
    checks = {
        "classes_exact": classes == expected_classes,
        "all_rows_grid_schema": len(rows) == 6400
        and all(row.get("schema") == GRID_SCHEMA for row in rows),
        "unique_tasks_exact": int(input_audit.get("unique_tasks", -1)) == 6400,
        "no_duplicate_records": int(input_audit.get("duplicate_records", 0)) == 0,
        "no_conflicting_success": int(input_audit.get("conflicting_success_records", 0)) == 0,
        "rows_per_split_exact": by_split == Counter({"train": 3200, "validation": 3200}),
        "sources_per_split_exact": all(len(sources.get(split, set())) == 100 for split in ("train", "validation")),
        "source_dates_exact": all(source_date_counts.get(split, {}) == expected_date_sources for split in ("train", "validation")),
        "opponents_exact": all(opponents.get(split, set()) == set(classes) for split in ("train", "validation")),
        "contexts_per_split_exact": context_counts == Counter({"train": 800, "validation": 800}),
        "candidate_grid_complete": not incomplete,
        "train_validation_source_disjoint": not source_overlap,
    }
    return {
        "required": True,
        "checks": checks,
        "passed": all(checks.values()),
        "rows_by_split": dict(by_split),
        "sources_by_split": {key: len(value) for key, value in sources.items()},
        "source_dates_by_split": source_date_counts,
        "contexts_by_split": dict(context_counts),
        "incomplete_contexts": len(incomplete),
        "incomplete_context_examples": list(incomplete.items())[:10],
        "source_overlap": len(source_overlap),
    }


def train_and_report(
    game_rows: Sequence[Mapping[str, Any]],
    registry: Registry,
    classes: Sequence[str],
    weights_path: Path,
    report_path: Path,
    ridge: float,
    min_support: int,
    rule_router_id: str | None,
    formal_grid: bool = False,
) -> dict[str, Any]:
    input_audit = dict(getattr(game_rows, "audit", {}))
    if int(input_audit.get("conflicting_success_records", 0)):
        raise ValueError(
            "same task_id has conflicting successful outcomes; refusing ambiguous grid"
        )
    data = perspectives(game_rows, registry)
    classes = tuple(str(item) for item in classes)
    roots = _root_lineages(registry, classes)
    train_rows = [row for row in data if row.split == "train"]
    validation_rows = [row for row in data if row.split == "validation"]
    test_rows = [row for row in data if row.split == "test"]
    split_by_source: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    split_by_seed: dict[int, set[str]] = defaultdict(set)
    split_by_episode: dict[str, set[str]] = defaultdict(set)
    for row in data:
        split_by_source[(row.date, row.episode_id, row.seed)].add(row.split)
        split_by_seed[row.seed].add(row.split)
        split_by_episode[row.episode_id].add(row.split)
    leakage = {str(key): sorted(value) for key, value in split_by_source.items() if len(value) != 1}
    seed_leakage = {str(key): sorted(value) for key, value in split_by_seed.items() if len(value) != 1}
    episode_leakage = {str(key): sorted(value) for key, value in split_by_episode.items() if len(value) != 1}
    if leakage or seed_leakage or episode_leakage:
        raise ValueError(
            "seed/episode appears in multiple splits: "
            f"source={list(leakage.items())[:3]} "
            f"seed={list(seed_leakage.items())[:3]} "
            f"episode={list(episode_leakage.items())[:3]}"
        )
    run_fingerprints: dict[str, set[str]] = defaultdict(set)
    for row in game_rows:
        source = row.get("source") or {}
        split = _normalise_split(source.get("split"))
        fingerprint = row.get("collection_fingerprint") or row.get("run_fingerprint")
        if split and fingerprint:
            run_fingerprints[split].add(str(fingerprint))
    mixed = {key: sorted(value) for key, value in run_fingerprints.items() if len(value) != 1}
    if mixed:
        raise ValueError(f"multiple evaluation fingerprints inside one split: {mixed}")
    if not train_rows or not validation_rows:
        raise ValueError("training requires both train and validation outcome grids")
    if test_rows:
        raise ValueError(
            "pre-selection trainer refuses test rows; open the official test panel once, "
            "only in the final fixed-vs-rule-vs-learned matrix"
        )
    grid_rows = [row for row in game_rows if row.get("schema") == GRID_SCHEMA]
    if grid_rows:
        bad = [
            row for row in grid_rows
            if row.get("error") is not None or not row.get("done")
            or not row.get("prefix_complete") or not row.get("prefix_match")
            or row.get("switch_features") is None
            or not row.get("switch_feature_sha256")
        ]
        if bad:
            raise ValueError(f"router outcome grid contains {len(bad)} invalid/prefix-incompatible rows")
        collections = {str(row.get("collection_fingerprint") or "") for row in grid_rows}
        registries = {str(row.get("registry_sha256") or "") for row in grid_rows}
        implementations = {
            str(row.get("collection_implementation_sha256") or "") for row in grid_rows
        }
        if (
            len(collections) != 1
            or "" in collections
            or len(registries) != 1
            or "" in registries
            or len(implementations) != 1
            or "" in implementations
        ):
            raise ValueError(
                "router grid mixes collection, implementation, or registry fingerprints"
            )
        current_registry_hash = registry_fingerprint(registry)
        if registries != {current_registry_hash}:
            raise ValueError(
                "router grid registry/code fingerprint differs from current registry"
            )
        if implementations != {grid_implementation_fingerprint()}:
            raise ValueError(
                "router grid collector implementation differs from current collector"
            )
    formal_audit = formal_grid_audit(grid_rows, classes, input_audit)
    formal_audit["required"] = bool(formal_grid)
    if formal_grid and not formal_audit["passed"]:
        failed = [
            key for key, value in formal_audit["checks"].items() if not value
        ]
        raise ValueError(f"formal Router grid gate failed: {failed}")

    if rule_router_id:
        rule_spec = dict(registry.require(rule_router_id))
    else:
        rule_spec = default_rule_spec(classes)
    expert_specs = {item: registry.require(item) for item in classes}
    rule_selector = RuleSelector(rule_spec, expert_specs, classes[0])

    lolo = {}
    for held in sorted(set(roots.values())):
        # LOLO holds out the *opponent* root lineage only.  All four candidate
        # experts remain selectable; deleting the same-named candidate would
        # confound opponent generalisation with a smaller action space.
        fold_classes = list(classes)
        fold_train = [row for row in train_rows if row.opponent_lineage != held]
        fold_eval = [row for row in validation_rows if row.opponent_lineage == held]
        fold_model = fit_heads(fold_train, fold_classes, ridge, min_support)
        fixed_rank = _training_rank(fold_train, fold_classes)
        fold_rule = RuleSelector(rule_spec, {item: expert_specs[item] for item in fold_classes}, fold_classes[0])
        evaluation = evaluate_policies(fold_eval, fold_classes, fold_model, fixed_rank, fold_rule, held)
        lolo[held] = {
            "held_root_lineage": held,
            "excluded_candidate_classes": [],
            "held_lineage_absent_from_training_opponents": all(
                row.opponent_lineage != held for row in fold_train
            ),
            "train_rows": len(fold_train), "evaluation_rows": len(fold_eval),
            "training_support": fold_model.support, "best_fixed_rank": fixed_rank,
            "comparison": evaluation,
        }

    # Report validation only from a train-only fit.  Afterwards, with schema
    # and hyperparameters frozen, refit train+validation for the later sealed
    # test matrix; never score this refit on its own training validation rows.
    validation_model = fit_heads(train_rows, classes, ridge, min_support)
    validation_rank = _training_rank(train_rows, classes)
    validation_comparison = evaluate_policies(
        validation_rows, classes, validation_model, validation_rank, rule_selector, None
    )
    final_fit_rows = [*train_rows, *validation_rows]
    final_model = fit_heads(final_fit_rows, classes, ridge, min_support)
    final_rank = _training_rank(final_fit_rows, classes)
    save_weights(final_model, weights_path)
    weights_sha256 = _file_sha256(weights_path.resolve())
    report = {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_schema": FEATURE_SCHEMA,
        "feature_dim": FEATURE_DIM,
        "public_features_only": True,
        "private_observation_used": False,
        "training_implementation_sha256": training_implementation_fingerprint(),
        "registry_and_code_sha256": registry_fingerprint(registry),
        "input_jsonl_audit": input_audit,
        "formal_grid_audit": formal_audit,
        "classes": list(classes), "root_lineage": roots,
        "rows": {"all": len(data), "train": len(train_rows), "validation": len(validation_rows), "test_seen": 0},
        "run_fingerprints_by_split": {key: sorted(value) for key, value in run_fingerprints.items()},
        "fit_splits": ["train", "validation"],
        "test_used_for_fit": False,
        "pre_selection_test_access": False,
        "ridge": ridge, "minimum_support": min_support,
        "frozen_rule_spec": rule_spec,
        "final_support": final_model.support, "best_fixed_rank": final_rank,
        "weights": str(weights_path.resolve()),
        "weights_sha256": weights_sha256,
        "leave_one_root_lineage_out": lolo,
        "validation_comparison_train_only_fit": validation_comparison,
        "acceptance": {
            "lolo_all_have_contexts": all(fold["comparison"]["contexts"] > 0 for fold in lolo.values()),
            # These are validation diagnostics, not deployment gates.  The
            # sole unbiased comparison is the later, frozen test matrix.
            "learned_beats_fixed_validation": (
                validation_comparison["learned_minus_fixed"] is not None
                and validation_comparison["learned_minus_fixed"] > 0
            ),
            "learned_beats_rule_validation": (
                validation_comparison["learned_minus_rule"] is not None
                and validation_comparison["learned_minus_rule"] > 0
            ),
            "rule_non_degenerate": (
                len(validation_comparison["selection_counts"]["rule_router"]) >= 2
                and len(validation_comparison["rule_reason_counts"]) >= 2
                and validation_comparison["rule_reason_max_share"] is not None
                and validation_comparison["rule_reason_max_share"] < 0.95
            ),
            "learned_non_degenerate": len(validation_comparison["selection_counts"]["learned_router"]) >= 2,
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _ids(values: Sequence[str]) -> list[str]:
    result = []
    for value in values:
        result.extend(item.strip() for item in str(value).split(",") if item.strip())
    return list(dict.fromkeys(result))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=Path, nargs="+", required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--experts", nargs="+", required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--ridge", type=float, default=10.0)
    parser.add_argument("--min-support", type=int, default=20)
    parser.add_argument("--rule-router-id")
    parser.add_argument(
        "--formal-grid",
        action="store_true",
        help="require the preregistered exact 6,400-row train/validation grid",
    )
    args = parser.parse_args()
    registry = load_registry(args.registry)
    classes = _ids(args.experts)
    for item in classes:
        registry.require(item)
    report = train_and_report(
        _read_jsonl(args.games), registry, classes, args.weights, args.report,
        args.ridge, args.min_support, args.rule_router_id, args.formal_grid,
    )
    print(json.dumps({"report": str(args.report), "weights": str(args.weights), "acceptance": report["acceptance"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
