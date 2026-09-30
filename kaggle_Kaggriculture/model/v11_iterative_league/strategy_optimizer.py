#!/usr/bin/env python3
"""Diagnose one V11 league round and admit one auditable pending candidate.

The optimiser consumes completed closed-loop league evidence.  It never uses a
sealed test row, never evaluates its new candidate as performance evidence on
the design panel, and never changes an existing model in place.  Candidate
admission requires Python compilation, six development seeds in both seats,
720 engine steps with DONE/DONE, zero stderr, and at least one counterfactual
action difference from the direct parent.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import redirect_stderr
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import py_compile
import random
import re
import sys
import time
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

try:
    from .mutation_catalog import (
        CATALOG,
        canonical_action,
        choose_mutation,
        mutation_record,
        mutation_signature,
        parameterizations,
        tried_mutations,
    )
    from .replay_inspector import action_digest, rerun_match
except ImportError:  # direct-script CLI
    from mutation_catalog import (
        CATALOG,
        canonical_action,
        choose_mutation,
        mutation_record,
        mutation_signature,
        parameterizations,
        tried_mutations,
    )
    from replay_inspector import action_digest, rerun_match


HERE = Path(__file__).resolve().parent
V10_FACTORY = HERE.parent / "v10_replay_lolo_router" / "agent_factory.py"
SCHEMA = "kaggriculture-v11-strategy-diagnosis-1"
CATASTROPHIC_MIN_DIRECT_GAMES = 200
CATASTROPHIC_MAX_SCORE_RATE = 0.20
CATASTROPHIC_MAX_MEAN_MARGIN = -5000.0
TRANSFER_MIN_LINEAGES = 2
TRANSFER_MIN_SCORE_RATE = 0.55
DEFAULT_DATA_ROOT = (
    HERE.parents[1]
    / "model_data"
    / "kaggriculture_episodes_index"
    / "daily"
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
            if isinstance(row, Mapping):
                rows.append(dict(row))
    if not rows:
        raise ValueError(f"no league rows in {path}")
    return rows


def _load_factory():
    name = f"_v11_optimizer_factory_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(name, V10_FACTORY)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load V10 agent factory: {V10_FACTORY}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalise_split(value: Any) -> str:
    split = str(value or "").strip().lower()
    return "validation" if split == "val" else split


def assert_no_sealed_test(
    rows: Sequence[Mapping[str, Any]], summary: Mapping[str, Any] | None = None
) -> None:
    """Fail closed if any design input advertises sealed-test provenance."""

    if summary:
        provenance = summary.get("provenance") or summary.get("panel") or {}
        if _normalise_split(provenance.get("split")) == "test":
            raise ValueError("sealed test summary cannot be used by strategy optimiser")
        declared_splits = set()
        panel = summary.get("panel") or {}
        declared_splits.update(_normalise_split(item) for item in (panel.get("splits") or []))
        declared_splits.update(
            _normalise_split(item) for item in ((summary.get("provenance") or {}).get("source_splits") or [])
        )
        if "test" in declared_splits:
            raise ValueError("sealed test split declared by league summary")
        if summary.get("sealed_test") is True or summary.get("test_used") is True:
            raise ValueError("summary declares sealed-test use")
    for index, row in enumerate(rows):
        source = row.get("source") if isinstance(row.get("source"), Mapping) else {}
        split = _normalise_split(source.get("split"))
        if split == "test":
            raise ValueError(f"sealed test row forbidden at index {index}")
        if split not in {"train", "validation"}:
            raise ValueError(
                f"strategy optimiser requires an explicit development split at index {index}: {split!r}"
            )


def validate_league_round(
    rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    source_round: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate the completed formal round and deduplicate successful retries."""

    assert_no_sealed_test(rows, summary)
    if int(summary.get("round", -1)) != int(source_round):
        raise ValueError("league summary round differs from requested source_round")
    if summary.get("complete") is not True:
        raise ValueError("strategy optimisation requires a complete formal league round")
    panel = summary.get("panel") or {}
    if int(panel.get("count", 0)) != 100 or int(panel.get("unique_seeds", 0)) != 100:
        raise ValueError("league round must use exactly 100 unique official seeds")
    if set(panel.get("date_counts") or {}) != {
        "2026-08-18",
        "2026-08-19",
        "2026-08-20",
    }:
        raise ValueError("league round dates are not exactly 2026-08-18..20")
    if not set(_normalise_split(item) for item in (panel.get("splits") or [])).issubset(
        {"train", "validation"}
    ):
        raise ValueError("league panel contains a non-development split")
    if (summary.get("panel_integrity") or {}).get("all_pairs_share_exact_panel") is not True:
        raise ValueError("league pairs did not share the exact same seed/seat panel")
    run_fingerprint = str(summary.get("run_fingerprint") or "")
    successes: dict[str, dict[str, Any]] = {}
    semantic: dict[str, str] = {}
    ignored_failed_attempts = 0
    ignored_foreign_rows = 0
    identical_success_duplicates = 0
    for raw in rows:
        row = dict(raw)
        if str(row.get("run_fingerprint") or "") != run_fingerprint:
            ignored_foreign_rows += 1
            continue
        task_id = str(row.get("task_id") or "")
        success = row.get("error") is None and row.get("done") is True and row.get("score_a") is not None
        if not success:
            ignored_failed_attempts += 1
            continue
        digest = _sha256_bytes(
            _stable_json(
                {
                    key: row.get(key)
                    for key in (
                        "task_id",
                        "model_a",
                        "model_b",
                        "model_a_seat",
                        "source",
                        "statuses",
                        "rewards",
                        "score_a",
                        "margin_a",
                    )
                }
            ).encode()
        )
        if task_id in successes:
            if semantic[task_id] != digest:
                raise ValueError(f"conflicting successful retry for task_id={task_id}")
            identical_success_duplicates += 1
            continue
        successes[task_id] = row
        semantic[task_id] = digest
    expected = int(summary.get("valid_games", -1))
    if len(successes) != expected or expected != int(summary.get("scheduled_games", -2)):
        raise ValueError(
            f"deduplicated league rows mismatch: successes={len(successes)}, "
            f"summary_valid={expected}, scheduled={summary.get('scheduled_games')}"
        )
    model_ids = [str(item) for item in (summary.get("model_ids") or [])]
    expected_pairs = len(model_ids) * (len(model_ids) - 1) // 2
    if int(summary.get("expected_pairs", -1)) != expected_pairs or int(
        summary.get("complete_pairs", -1)
    ) != expected_pairs:
        raise ValueError("league pair count is incomplete")
    return list(successes.values()), {
        "raw_rows": len(rows),
        "deduplicated_successes": len(successes),
        "ignored_failed_attempts": ignored_failed_attempts,
        "ignored_foreign_rows": ignored_foreign_rows,
        "identical_success_duplicates": identical_success_duplicates,
        "formal_round_complete": True,
        "panel_count": 100,
        "sealed_test_used": False,
    }


def _perspectives(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    model_a = str(row.get("model_a") or "")
    model_b = str(row.get("model_b") or "")
    if not model_a or not model_b:
        return []
    a_seat = int(row.get("model_a_seat", 0) or 0)
    valid = row.get("error") is None and row.get("done") is True
    if valid and row.get("score_a") is not None:
        score_a = float(row["score_a"])
        margin_a = float(row.get("margin_a", 0.0) or 0.0)
        reward_a = row.get("reward_a")
        reward_b = row.get("reward_b")
        if reward_b is None:
            rewards = row.get("rewards") or []
            reward_b = rewards[1 - a_seat] if len(rewards) > 1 else None
    else:
        # An unattributed evaluator failure is retained as an alert rather than
        # silently disappearing.  It cannot be assigned to one model from the
        # V10 schema, so both perspectives receive no competitive score.
        score_a = math.nan
        margin_a = math.nan
        reward_a = None
        reward_b = None
    source = dict(row.get("source") or {})
    common = {
        "task_id": str(row.get("task_id") or ""),
        "pair_id": str(row.get("pair_id") or f"{model_a}__vs__{model_b}"),
        "source": source,
        "valid": valid,
        "error": row.get("error"),
        "raw": row,
    }
    return [
        {
            **common,
            "model": model_a,
            "opponent": model_b,
            "seat": a_seat,
            "score": score_a,
            "margin": margin_a,
            "reward": float(reward_a) if reward_a is not None else None,
        },
        {
            **common,
            "model": model_b,
            "opponent": model_a,
            "seat": 1 - a_seat,
            "score": 1.0 - score_a if math.isfinite(score_a) else math.nan,
            "margin": -margin_a if math.isfinite(margin_a) else math.nan,
            "reward": float(reward_b) if reward_b is not None else None,
        },
    ]


@dataclass
class Slice:
    games: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    points: float = 0.0
    margins: list[float] = field(default_factory=list)
    rewards: list[float] = field(default_factory=list)
    errors: int = 0

    def add(self, item: Mapping[str, Any]) -> None:
        self.games += 1
        score = float(item.get("score", math.nan))
        if not math.isfinite(score):
            self.errors += 1
            return
        self.points += score
        if score > 0.5:
            self.wins += 1
        elif score < 0.5:
            self.losses += 1
        else:
            self.draws += 1
        margin = float(item.get("margin", math.nan))
        if math.isfinite(margin):
            self.margins.append(margin)
        reward = item.get("reward")
        if reward is not None and math.isfinite(float(reward)):
            self.rewards.append(float(reward))

    def record(self) -> dict[str, Any]:
        array = np.asarray(self.margins, dtype=np.float64)
        return {
            "games": self.games,
            "valid_games": self.games - self.errors,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "points": self.points,
            "score_rate": self.points / max(1, self.games - self.errors),
            "mean_margin": float(np.mean(array)) if len(array) else None,
            "median_margin": float(np.median(array)) if len(array) else None,
            "margin_q05": float(np.quantile(array, 0.05)) if len(array) else None,
            "margin_q95": float(np.quantile(array, 0.95)) if len(array) else None,
            "mean_reward": float(np.mean(self.rewards)) if self.rewards else None,
            "errors": self.errors,
        }


def compute_diagnostics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    totals: defaultdict[str, Slice] = defaultdict(Slice)
    by_opponent: defaultdict[str, defaultdict[str, Slice]] = defaultdict(
        lambda: defaultdict(Slice)
    )
    by_date: defaultdict[str, defaultdict[str, Slice]] = defaultdict(
        lambda: defaultdict(Slice)
    )
    by_seat: defaultdict[str, defaultdict[str, Slice]] = defaultdict(
        lambda: defaultdict(Slice)
    )
    perspectives = []
    for row in rows:
        for item in _perspectives(row):
            perspectives.append(item)
            model = item["model"]
            totals[model].add(item)
            by_opponent[model][item["opponent"]].add(item)
            date = str(item["source"].get("date") or item["source"].get("source_date") or "unknown")[:10]
            by_date[model][date].add(item)
            by_seat[model][str(item["seat"])].add(item)
    standings = []
    for model, aggregate in totals.items():
        row = {"model_id": model, **aggregate.record()}
        opponent_rates = [
            value.record()["score_rate"] for value in by_opponent[model].values()
        ]
        row["worst_opponent_score_rate"] = min(opponent_rates) if opponent_rates else None
        standings.append(row)
    standings.sort(
        key=lambda row: (
            -float(row["points"]),
            -float(row["mean_margin"] if row["mean_margin"] is not None else -math.inf),
            str(row["model_id"]),
        )
    )
    for rank, row in enumerate(standings, 1):
        row["rank"] = rank
    models = {
        model: {
            "overall": totals[model].record(),
            "by_opponent": {
                key: value.record() for key, value in sorted(by_opponent[model].items())
            },
            "by_date": {
                key: value.record() for key, value in sorted(by_date[model].items())
            },
            "by_seat": {
                key: value.record() for key, value in sorted(by_seat[model].items())
            },
        }
        for model in sorted(totals)
    }
    leader = standings[0]["model_id"] if standings else None
    lowest = standings[-1]["model_id"] if standings else None
    gap_sources = []
    if leader and lowest and leader != lowest:
        opponents = sorted(
            set(models[leader]["by_opponent"]) | set(models[lowest]["by_opponent"])
        )
        for opponent in opponents:
            if opponent in {leader, lowest}:
                continue
            high = models[leader]["by_opponent"].get(opponent, {})
            low = models[lowest]["by_opponent"].get(opponent, {})
            if high and low:
                gap_sources.append(
                    {
                        "opponent": opponent,
                        "leader_score_rate": high["score_rate"],
                        "lowest_score_rate": low["score_rate"],
                        "score_rate_gap": high["score_rate"] - low["score_rate"],
                        "mean_margin_gap": (high["mean_margin"] or 0.0)
                        - (low["mean_margin"] or 0.0),
                    }
                )
        gap_sources.sort(key=lambda item: item["score_rate_gap"], reverse=True)
    return {
        "standings": standings,
        "models": models,
        "leader": leader,
        "lowest": lowest,
        "leader_vs_lowest_total_point_gap": (
            standings[0]["points"] - standings[-1]["points"] if standings else None
        ),
        "leader_vs_lowest_gap_sources": gap_sources,
        "perspectives": perspectives,
    }


def select_representative_losses(
    diagnostics: Mapping[str, Any], model_id: str, count: int = 3
) -> list[dict[str, Any]]:
    model_games = [
        item
        for item in diagnostics.get("perspectives", [])
        if item["model"] == model_id
        and item["valid"]
        and _normalise_split(item["source"].get("split")) != "test"
    ]
    losses = [item for item in model_games if float(item["score"]) == 0.0]
    if not model_games:
        return []
    selected: list[tuple[str, dict[str, Any]]] = []
    if losses:
        selected.append(("惨败", min(losses, key=lambda item: float(item["margin"]))))
        selected.append(("窄负", max(losses, key=lambda item: float(item["margin"]))))
        opponent_losses = Counter(item["opponent"] for item in losses)
        repeated_opponent = sorted(opponent_losses, key=lambda name: (-opponent_losses[name], name))[0]
        repeated = sorted(
            [item for item in losses if item["opponent"] == repeated_opponent],
            key=lambda item: float(item["margin"]),
        )
        selected.append(("特定谱系反复失败", repeated[len(repeated) // 2]))
    unique = []
    seen = set()
    for category, item in selected:
        key = (
            str(item["source"].get("date")),
            str(item["source"].get("episode_id")),
            int(item["source"].get("seed", 0)),
            int(item["seat"]),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "category": category,
                "model": item["model"],
                "opponent": item["opponent"],
                "model_seat": item["seat"],
                "margin": item["margin"],
                "reward": item["reward"],
                "source": item["source"],
                "task_id": item["task_id"],
            }
        )
    # An undefeated or near-undefeated leader can still be improved.  Fill any
    # missing slots with its lowest-score/lowest-margin stress games, labelled
    # honestly rather than misreporting them as losses.
    for item in sorted(
        model_games,
        key=lambda value: (float(value["score"]), float(value["margin"])),
    ):
        if len(unique) >= count:
            break
        key = (
            str(item["source"].get("date")),
            str(item["source"].get("episode_id")),
            int(item["source"].get("seed", 0)),
            int(item["seat"]),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "category": "低分压力局" if float(item["score"]) > 0.0 else "补充败局",
                "model": item["model"],
                "opponent": item["opponent"],
                "model_seat": item["seat"],
                "margin": item["margin"],
                "reward": item["reward"],
                "source": item["source"],
                "task_id": item["task_id"],
            }
        )
    return unique[:count]


def _aggregate_findings(reruns: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counter = Counter()
    for rerun in reruns:
        counter.update((rerun.get("events") or {}).get("findings") or {})
    return dict(sorted(counter.items()))


def _registry_specs(registry_path: Path) -> tuple[Any, list[dict[str, Any]]]:
    factory = _load_factory()
    registry = factory.load_registry(registry_path)
    return registry, [dict(spec) for spec in registry.models.values()]


def _registered_parent_id(spec: Mapping[str, Any]) -> str:
    parents = list(spec.get("parent_models") or [])
    if parents:
        return str(parents[0])
    kwargs = spec.get("factory_kwargs") or {}
    if kwargs.get("parent_id"):
        return str(kwargs["parent_id"])
    lineage = list(spec.get("lineage") or [])
    if len(lineage) >= 2:
        return str(lineage[0])
    model_id = str(spec.get("id") or "")
    for prefix in ("v1", "v2", "v5", "v8"):
        if model_id.startswith(prefix + "_"):
            return f"baseline_{prefix}"
    return ""


def _registered_mutation(spec: Mapping[str, Any]) -> tuple[str, str]:
    """Return mutation name and evidence quality (explicit or inferred alias)."""

    explicit = str(spec.get("mutation") or "")
    if explicit in CATALOG:
        return explicit, "explicit"
    text = " ".join(
        [
            str(spec.get("id") or ""),
            str(spec.get("family") or ""),
            " ".join(str(item) for item in (spec.get("tags") or [])),
        ]
    ).lower()
    for name, mutation in CATALOG.items():
        if name.lower() in text or any(
            str(alias).lower() in text for alias in mutation.aliases
        ):
            return name, "inferred_alias"
    return "", ""


def registered_mutation_evidence(
    diagnosis: Mapping[str, Any], registry_specs: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Rank mechanisms from completed direct child-vs-parent development games.

    A catastrophic candidate with an explicit mutation field or an unambiguous
    registered alias excludes the whole mechanism family, rather than inviting
    a threshold retune on the same failed idea.  Transfer priority requires
    positive direct evidence in at least two distinct parent lineages, so a
    mechanism is never promoted merely because its name or one replay looked
    attractive.
    """

    models = diagnosis.get("models") or {}
    rows = []
    for raw in registry_specs:
        spec = dict(raw)
        child = str(spec.get("id") or "")
        parent = _registered_parent_id(spec)
        mutation, mapping_source = _registered_mutation(spec)
        if not child or not parent or not mutation or child == parent:
            continue
        child_model = models.get(child) or {}
        parent_model = models.get(parent) or {}
        direct = (child_model.get("by_opponent") or {}).get(parent)
        if not direct or not parent_model:
            continue
        games = int(direct.get("games", 0) or 0)
        valid_games = int(direct.get("valid_games", games) or 0)
        score_rate = float(direct.get("score_rate", math.nan))
        mean_margin = direct.get("mean_margin")
        if (
            games <= 0
            or valid_games != games
            or not math.isfinite(score_rate)
            or mean_margin is None
            or not math.isfinite(float(mean_margin))
        ):
            continue
        rows.append(
            {
                "child": child,
                "parent": parent,
                "mutation": mutation,
                "mapping_source": mapping_source,
                "games": games,
                "wins": int(direct.get("wins", 0) or 0),
                "draws": int(direct.get("draws", 0) or 0),
                "losses": int(direct.get("losses", 0) or 0),
                "score_rate": score_rate,
                "mean_margin": float(mean_margin),
            }
        )

    catastrophic = []
    for row in rows:
        if (
            row["mapping_source"] in {"explicit", "inferred_alias"}
            and row["games"] >= CATASTROPHIC_MIN_DIRECT_GAMES
            and row["score_rate"] <= CATASTROPHIC_MAX_SCORE_RATE
            and row["mean_margin"] <= CATASTROPHIC_MAX_MEAN_MARGIN
        ):
            catastrophic.append(dict(row))
    excluded = sorted({row["mutation"] for row in catastrophic})

    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["mutation"] not in excluded:
            grouped[row["mutation"]].append(row)
    groups = []
    for mutation, evidence_rows in sorted(grouped.items()):
        by_parent: defaultdict[str, list[float]] = defaultdict(list)
        games = 0
        points = 0.0
        for row in evidence_rows:
            if row["games"] < CATASTROPHIC_MIN_DIRECT_GAMES:
                continue
            by_parent[row["parent"]].append(float(row["score_rate"]))
            games += int(row["games"])
            points += float(row["score_rate"]) * int(row["games"])
        lineage_rates = {
            parent: float(np.mean(values)) for parent, values in sorted(by_parent.items())
        }
        lineage_count = len(lineage_rates)
        minimum = min(lineage_rates.values()) if lineage_rates else None
        weighted = points / games if games else None
        strong = bool(
            lineage_count >= TRANSFER_MIN_LINEAGES
            and minimum is not None
            and minimum >= TRANSFER_MIN_SCORE_RATE
            and all(value > 0.5 for value in lineage_rates.values())
        )
        groups.append(
            {
                "mutation": mutation,
                "lineage_count": lineage_count,
                "lineage_score_rates": lineage_rates,
                "minimum_lineage_score_rate": minimum,
                "weighted_direct_score_rate": weighted,
                "direct_games": games,
                "strong_transfer_evidence": strong,
            }
        )
    strong_groups = [item for item in groups if item["strong_transfer_evidence"]]
    strong_groups.sort(
        key=lambda item: (
            -int(item["lineage_count"]),
            -float(item["minimum_lineage_score_rate"]),
            -float(item["weighted_direct_score_rate"]),
            str(item["mutation"]),
        )
    )
    return {
        "schema": "kaggriculture-v11-registered-mutation-evidence-1",
        "source": "completed development round direct child-vs-parent games only",
        "thresholds": {
            "catastrophic_min_direct_games": CATASTROPHIC_MIN_DIRECT_GAMES,
            "catastrophic_max_score_rate": CATASTROPHIC_MAX_SCORE_RATE,
            "catastrophic_max_mean_margin": CATASTROPHIC_MAX_MEAN_MARGIN,
            "transfer_min_lineages": TRANSFER_MIN_LINEAGES,
            "transfer_min_score_rate": TRANSFER_MIN_SCORE_RATE,
        },
        "direct_evidence": rows,
        "catastrophic_evidence": catastrophic,
        "excluded_mutations": excluded,
        "mechanism_groups": groups,
        "strong_transfer_priority": [item["mutation"] for item in strong_groups],
    }


def build_parameter_candidates(
    parent_id: str,
    selected_name: str,
    selected_params: Mapping[str, Any],
    registry_specs: Sequence[Mapping[str, Any]],
    evidence: Mapping[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    """Build an auditable order without retrying an excluded mutation family."""

    exact_tried = tried_mutations(registry_specs)
    excluded = {str(item) for item in (evidence.get("excluded_mutations") or [])}
    ordered_names = [
        *[str(item) for item in (evidence.get("strong_transfer_priority") or [])],
        str(selected_name),
        *list(CATALOG),
    ]
    ordered_names = [
        name for name in dict.fromkeys(ordered_names) if name in CATALOG and name not in excluded
    ]
    result: list[tuple[str, dict[str, Any]]] = []
    for name in ordered_names:
        candidates = parameterizations(name)
        if name == selected_name:
            candidates = [dict(selected_params), *candidates]
        for params in candidates:
            params = dict(params)
            signature = mutation_signature(parent_id, name, params)
            if signature in exact_tried or (name, params) in result:
                continue
            result.append((name, params))
    return result


def _rebase_spec(
    spec: Mapping[str, Any], source_parent: Path, output_parent: Path
) -> dict[str, Any]:
    result = deepcopy(dict(spec))
    for key in ("path", "module_path", "weights"):
        value = result.get(key)
        if value:
            path = Path(str(value)).expanduser()
            resolved = path.resolve() if path.is_absolute() else (source_parent / path).resolve()
            result[key] = os.path.relpath(resolved, output_parent.resolve())
    if result.get("code_paths"):
        result["code_paths"] = [
            os.path.relpath(
                (
                    Path(str(value)).expanduser().resolve()
                    if Path(str(value)).expanduser().is_absolute()
                    else (source_parent / str(value)).resolve()
                ),
                output_parent.resolve(),
            )
            for value in result["code_paths"]
        ]
    return result


def _candidate_entry(
    candidate_id: str,
    parent_id: str,
    mutation_name: str,
    mutation_params: Mapping[str, Any],
    registry_path: Path,
    source_round: int,
) -> dict[str, Any]:
    return {
        "id": candidate_id,
        "kind": "python",
        "path": os.path.relpath(HERE / "candidate_agent.py", registry_path.parent),
        "factory": "create_agent",
        "factory_kwargs": {
            "parent_registry": os.path.relpath(registry_path, HERE),
            "parent_id": parent_id,
            "mutation_name": mutation_name,
            "mutation_params": dict(mutation_params),
            "candidate_id": candidate_id,
        },
        "code_paths": [
            os.path.relpath(HERE / "candidate_agent.py", registry_path.parent),
            os.path.relpath(HERE / "mutation_catalog.py", registry_path.parent),
        ],
        "family": f"{parent_id}+{mutation_name}",
        "lineage": [parent_id, candidate_id],
        "parent_models": [parent_id],
        "mutation": mutation_name,
        "change_scope": mutation_record(mutation_name)["change_scope"],
        "tags": [
            "pending",
            "v11",
            "market-residual",
            f"mutation:{mutation_name}",
            f"source_round:{source_round}",
            f"first_evaluation_round:{source_round + 1}",
        ],
        "source_round": source_round,
        "first_evaluation_round": source_round + 1,
    }


def _write_registry_payload(
    input_registry: Path,
    output_registry: Path,
    candidate_entry: Mapping[str, Any],
) -> dict[str, Any]:
    factory = _load_factory()
    source = factory.load_registry(input_registry)
    models = [
        _rebase_spec(spec, input_registry.parent, output_registry.parent)
        for spec in source.models.values()
    ]
    candidate_id = str(candidate_entry["id"])
    if candidate_id in source.models:
        raise ValueError(f"candidate id already exists: {candidate_id}")
    models.append(dict(candidate_entry))
    # Candidate registries are an append-only continuation of the sealed Fast
    # registry.  Do not truncate the source-manifest, Router-fit exclusion,
    # equivalence, or pre-test provenance after the first candidate.
    preserved = {
        key: deepcopy(value)
        for key, value in source.raw.items()
        if key
        not in {
            "schema",
            "models",
            "agents",
            "created_at",
            "candidate_parent_registry",
            "candidate_parent_registry_file_sha256",
            "pending_candidate",
        }
    }
    return {
        **preserved,
        "schema": "kaggriculture-v11-pending-candidate-registry-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate_parent_registry": str(input_registry.resolve()),
        "candidate_parent_registry_file_sha256": _sha256_file(input_registry),
        "candidate_parent_registry_and_code_sha256": factory.registry_fingerprint(source),
        "pending_candidate": candidate_id,
        "models": models,
    }


class _ActionRecorder:
    def __init__(self, agent: Any) -> None:
        self.agent = agent
        self.actions: list[dict[str, Any]] = []

    def __call__(self, obs: Any, configuration: Any = None):
        action = self.agent(obs, configuration)
        self.actions.append(canonical_action(action))
        return action


def _run_target_trajectory(
    registry_path: Path,
    target_id: str,
    opponent_id: str,
    target_seat: int,
    seed: int,
) -> dict[str, Any]:
    from kaggle_environments import make

    # Candidate and parent controls must start from the same process-global
    # RNG state.  Otherwise a stochastic parent can look action-distinct even
    # when the market residual never fired.  Reset once before construction
    # and again before the first agent call because imports/constructors may
    # consume randomness.
    rng_seed = (int(seed) * 2 + int(target_seat) + 0x11C0DE) % (2**32)
    random.seed(rng_seed)
    np.random.seed(rng_seed)
    factory = _load_factory()
    registry = factory.load_registry(registry_path)
    target_raw = factory.create_agent(registry, target_id)
    opponent_raw = factory.create_agent(registry, opponent_id)
    target = _ActionRecorder(target_raw)
    agents = [target, opponent_raw] if int(target_seat) == 0 else [opponent_raw, target]
    stderr = io.StringIO()
    random.seed(rng_seed)
    np.random.seed(rng_seed)
    with redirect_stderr(stderr):
        env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
        env.run(agents)
    return {
        "statuses": [str(state.status) for state in env.state],
        "steps": len(env.steps),
        "actions": target.actions,
        "stderr": stderr.getvalue(),
    }


def run_admission_smoke(
    input_registry: Path,
    smoke_registry: Path,
    candidate_id: str,
    parent_id: str,
    mutation_name: str,
    mutation_params: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    source_round: int,
    workers: int = 12,
) -> dict[str, Any]:
    """Run functionality-only candidate/control counterfactuals on 6x2 seeds."""

    unique_sources = []
    seen = set()
    for source in sources:
        if _normalise_split(source.get("split")) not in {"train", "validation"}:
            continue
        key = (str(source.get("date")), int(source.get("seed", 0)))
        if key in seen or not key[1]:
            continue
        seen.add(key)
        unique_sources.append(dict(source))
        if len(unique_sources) == 6:
            break
    if len(unique_sources) < 6:
        raise ValueError("candidate admission requires six unique non-test development seeds")
    py_compile.compile(str(HERE / "candidate_agent.py"), doraise=True)
    py_compile.compile(str(HERE / "mutation_catalog.py"), doraise=True)
    entry = _candidate_entry(
        candidate_id,
        parent_id,
        mutation_name,
        mutation_params,
        smoke_registry,
        source_round,
    )
    payload = _write_registry_payload(input_registry, smoke_registry, entry)
    smoke_registry.parent.mkdir(parents=True, exist_ok=True)
    smoke_registry.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    factory = _load_factory()
    input_registry_object = factory.load_registry(input_registry)
    smoke_registry_object = factory.load_registry(smoke_registry)
    raw_results: dict[tuple[int, int, str], dict[str, Any]] = {}
    jobs = []
    for source_index, source in enumerate(unique_sources):
        seed = int(source["seed"])
        for seat in (0, 1):
            jobs.append((source_index, seat, "candidate", candidate_id, seed))
            jobs.append((source_index, seat, "control", parent_id, seed))
    if int(workers) <= 1:
        for source_index, seat, kind, target_id, seed in jobs:
            raw_results[(source_index, seat, kind)] = _run_target_trajectory(
                smoke_registry, target_id, parent_id, seat, seed
            )
    else:
        with ProcessPoolExecutor(max_workers=min(int(workers), len(jobs))) as pool:
            future_map = {
                pool.submit(
                    _run_target_trajectory,
                    smoke_registry,
                    target_id,
                    parent_id,
                    seat,
                    seed,
                ): (source_index, seat, kind)
                for source_index, seat, kind, target_id, seed in jobs
            }
            for future in as_completed(future_map):
                raw_results[future_map[future]] = future.result()
    trajectories = []
    all_done = True
    all_720 = True
    zero_stderr = True
    total_differences = 0
    changed_games = 0
    component_differences = Counter()
    for source_index, source in enumerate(unique_sources):
        seed = int(source["seed"])
        for seat in (0, 1):
            candidate = raw_results[(source_index, seat, "candidate")]
            control = raw_results[(source_index, seat, "control")]
            differences = 0
            local_components = Counter()
            for left, right in zip(candidate["actions"], control["actions"]):
                step_changed = False
                for component in ("market", "farmer", "hands"):
                    if left.get(component) != right.get(component):
                        local_components[component] += 1
                        step_changed = True
                differences += int(step_changed)
            length_difference = abs(len(candidate["actions"]) - len(control["actions"]))
            differences += length_difference
            if length_difference:
                local_components["trajectory_length"] += length_difference
            total_differences += differences
            component_differences.update(local_components)
            changed_games += int(differences > 0)
            all_done = all_done and candidate["statuses"] == ["DONE", "DONE"] and control[
                "statuses"
            ] == ["DONE", "DONE"]
            all_720 = all_720 and candidate["steps"] == 720 and control["steps"] == 720
            zero_stderr = zero_stderr and not candidate["stderr"] and not control["stderr"]
            trajectories.append(
                {
                    "date": str(source.get("date") or source.get("source_date") or "")[:10],
                    "episode_id": str(source.get("episode_id") or ""),
                    "seed": seed,
                    "target_seat": seat,
                    "candidate_done": candidate["statuses"] == ["DONE", "DONE"],
                    "control_done": control["statuses"] == ["DONE", "DONE"],
                    "candidate_steps": candidate["steps"],
                    "control_steps": control["steps"],
                    "candidate_calls": len(candidate["actions"]),
                    "control_calls": len(control["actions"]),
                    "candidate_action_sha256": _sha256_bytes(
                        _stable_json(candidate["actions"]).encode("utf-8")
                    ),
                    "control_action_sha256": _sha256_bytes(
                        _stable_json(control["actions"]).encode("utf-8")
                    ),
                    "action_difference_steps": differences,
                    "market_changed_steps": local_components["market"],
                    "farmer_changed_steps": local_components["farmer"],
                    "hands_changed_steps": local_components["hands"],
                    "stderr_bytes": len(candidate["stderr"].encode())
                    + len(control["stderr"].encode()),
                }
            )
    passed = all_done and all_720 and zero_stderr and changed_games > 0 and total_differences > 0
    return {
        "schema": "kaggriculture-v11-candidate-admission-smoke-1",
        "candidate_id": str(candidate_id),
        "parent_id": str(parent_id),
        "mutation_name": str(mutation_name),
        "mutation_params": dict(mutation_params),
        "input_registry": str(input_registry.resolve()),
        "input_registry_and_code_sha256": factory.registry_fingerprint(
            input_registry_object
        ),
        "smoke_registry": str(smoke_registry.resolve()),
        "smoke_registry_and_code_sha256": factory.registry_fingerprint(
            smoke_registry_object
        ),
        "development_sources": [
            {
                "date": str(item.get("date") or item.get("source_date") or "")[:10],
                "episode_id": str(item.get("episode_id") or ""),
                "seed": int(item["seed"]),
                "split": _normalise_split(item.get("split")),
            }
            for item in unique_sources
        ],
        "development_sources_sha256": _sha256_bytes(
            _stable_json(
                [
                    {
                        "date": str(item.get("date") or item.get("source_date") or "")[:10],
                        "episode_id": str(item.get("episode_id") or ""),
                        "seed": int(item["seed"]),
                        "split": _normalise_split(item.get("split")),
                    }
                    for item in unique_sources
                ]
            ).encode("utf-8")
        ),
        "functionality_only": True,
        "performance_evidence": False,
        "source_panel_reused_only_for_smoke": True,
        "source_round": source_round,
        "first_evaluation_round": source_round + 1,
        "minimum_seed_gate": 6,
        "seeds": len(unique_sources),
        "seat_assignments": 2,
        "candidate_games": 12,
        "parent_control_games": 12,
        "all_done": all_done,
        "all_720_steps": all_720,
        "zero_stderr": zero_stderr,
        "action_difference_steps": total_differences,
        "changed_games": changed_games,
        "market_changed_steps": component_differences["market"],
        "farmer_changed_steps": component_differences["farmer"],
        "hands_changed_steps": component_differences["hands"],
        "real_action_difference": total_differences > 0,
        "passed": passed,
        # Compatibility with the league admission reader.  These aggregate
        # aliases are true only when every candidate and control trajectory
        # passed the stronger 6-seed x 2-seat gate above.
        "done": passed,
        "statuses": ["DONE", "DONE"] if all_done else ["ERROR", "ERROR"],
        "steps": 720 if all_720 else 0,
        "trajectories": trajectories,
    }


def _candidate_id(round_number: int, parent_id: str, mutation_name: str) -> str:
    parent = re.sub(r"[^a-zA-Z0-9_]+", "_", parent_id).strip("_").lower()
    return f"r{round_number:03d}_{parent}_{mutation_name}"


def _smoke_sources(
    rows: Sequence[Mapping[str, Any]], representatives: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    sources = [dict(item["source"]) for item in representatives]
    for row in rows:
        if isinstance(row.get("source"), Mapping):
            sources.append(dict(row["source"]))
    # Prefer one seed per date before filling the remaining quota.
    by_date: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in sources:
        if _normalise_split(source.get("split")) in {"train", "validation"}:
            by_date[str(source.get("date") or source.get("source_date") or "")[:10]].append(source)
    ordered = []
    for date in sorted(by_date):
        if by_date[date]:
            ordered.append(by_date[date][0])
    ordered.extend(sources)
    return ordered


def _format_rate(value: Any) -> str:
    return "—" if value is None else f"{float(value):.3f}"


def render_markdown(diagnosis: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    ranking = diagnosis["standings"]
    lines = [
        f"# 第 {diagnosis['source_round']} 轮策略优化诊断",
        "",
        "> 本报告只使用本轮开发面板。新候选仅做功能 smoke；首次性能评测固定在下一轮全新面板。",
        "",
        "## 排名摘要",
        "",
        "| 排名 | 模型 | 积分 | 胜/平/负 | 得分率 | 平均金币差 | 最差对手得分率 |",
        "| ---: | --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in ranking:
        lines.append(
            f"| {row['rank']} | `{row['model_id']}` | {row['points']:.1f} | "
            f"{row['wins']}/{row['draws']}/{row['losses']} | {row['score_rate']:.3f} | "
            f"{_format_rate(row['mean_margin'])} | {_format_rate(row['worst_opponent_score_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## 领先模型诊断",
            "",
            f"领先模型：`{diagnosis['leader']}`；最低模型：`{diagnosis['lowest']}`；"
            f"总积分差：{diagnosis.get('leader_vs_lowest_total_point_gap', 0):.1f}。",
            "",
            "### 按对手",
            "",
            "| 对手 | 场次 | 得分率 | 平均金币差 |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    leader_diag = diagnosis["leader_diagnostics"]
    for opponent, row in leader_diag["by_opponent"].items():
        lines.append(
            f"| `{opponent}` | {row['games']} | {row['score_rate']:.3f} | {_format_rate(row['mean_margin'])} |"
        )
    for title, key in (("按日期", "by_date"), ("按席位", "by_seat")):
        lines.extend(
            [
                "",
                f"### {title}",
                "",
                "| 分组 | 场次 | 得分率 | 平均金币差 |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for name, row in leader_diag[key].items():
            lines.append(
                f"| {name} | {row['games']} | {row['score_rate']:.3f} | {_format_rate(row['mean_margin'])} |"
            )
    lines.extend(["", "## 代表性败局闭环重跑", ""])
    for item in diagnosis["representative_losses"]:
        source = item["source"]
        lines.append(
            f"- **{item['category']}**：对 `{item['opponent']}`，"
            f"{source.get('date')} / seed={source.get('seed')} / seat={item['model_seat']}，"
            f"金币差 {item['margin']:.0f}。"
        )
    findings = diagnosis.get("replay_findings") or {}
    lines.extend(
        [
            "",
            "动作级重跑保存的是活跃动作、市场/农场数值变化和每日快照，不保存整份原始 observation。",
            "",
            "主要事件计数："
            + (", ".join(f"{key}={value}" for key, value in findings.items()) or "未发现已编码安全事件"),
            "",
            "### 路线与事件摘要",
            "",
            "| 类别 | seed | 首次生产分叉 | 活跃动作 | 市场变化 | 农场变化 | 商店解锁事件 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in diagnosis.get("representative_replay_summaries") or []:
        lines.append(
            f"| {item['category']} | {item['seed']} | "
            f"{item['first_production_difference_step'] if item['first_production_difference_step'] is not None else '—'} | "
            f"{item['action_events']} | {item['market_events']} | {item['farm_events']} | {item['town_events']} |"
        )
    mutation_evidence = diagnosis.get("registered_mutation_evidence") or {}
    lines.extend(
        [
            "",
            "## 已注册残差的直接亲子证据",
            "",
            "| mutation | 独立父谱系 | 最差亲子得分率 | 加权亲子得分率 | 跨谱系优先 |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for item in mutation_evidence.get("mechanism_groups") or []:
        lines.append(
            f"| `{item['mutation']}` | {item['lineage_count']} | "
            f"{_format_rate(item['minimum_lineage_score_rate'])} | "
            f"{_format_rate(item['weighted_direct_score_rate'])} | "
            f"{'是' if item['strong_transfer_evidence'] else '否'} |"
        )
    excluded = mutation_evidence.get("excluded_mutations") or []
    lines.extend(
        [
            "",
            "灾难性亲子结果整族排除："
            + (", ".join(f"`{name}`" for name in excluded) if excluded else "无"),
        ]
    )
    lines.extend(
        [
            "",
            "## 新候选",
            "",
            f"- 模型：`{proposal['model_id']}`",
            f"- 直接父版本：`{proposal['parent_models'][0]}`",
            f"- 单一残差：`{proposal['mutation']['name']}`",
            f"- 变更范围：{proposal['change_scope']}",
            f"- 可证伪假设：{proposal['hypothesis']}",
            f"- 主要副作用：{proposal['risk']}",
            f"- 状态：`pending`；首次性能评测为第 {proposal['first_evaluation_round']} 轮全新面板。",
            "",
            "### 准入证据",
            "",
            f"6 个开发 seed × 双席位；候选 12 局与父版本对照 12 局；"
            f"720 回合、DONE/DONE、零 stderr：{proposal['smoke_evidence']['passed']}；"
            f"变化局数：{proposal['smoke_evidence']['changed_games']}；"
            f"动作差异步数：{proposal['smoke_evidence']['action_difference_steps']}；"
            f"market/farmer/hands：{proposal['smoke_evidence']['market_changed_steps']}/"
            f"{proposal['smoke_evidence']['farmer_changed_steps']}/"
            f"{proposal['smoke_evidence']['hands_changed_steps']}。",
            "",
            "> smoke 只证明可运行和非等价，不是性能结论。候选没有使用本轮面板给自己打无偏分数。",
        ]
    )
    return "\n".join(lines) + "\n"


def optimise_round(
    games_path: Path,
    summary_path: Path,
    registry_path: Path,
    output_dir: Path,
    source_round: int,
    data_root: Path | None = DEFAULT_DATA_ROOT,
    representative_count: int = 3,
) -> dict[str, Any]:
    games_path = games_path.expanduser().resolve()
    summary_path = summary_path.expanduser().resolve()
    registry_path = registry_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_rows = _read_jsonl(games_path)
    summary = _read_json(summary_path)
    rows, input_validation = validate_league_round(raw_rows, summary, source_round)
    diagnostics = compute_diagnostics(rows)
    # The league summary owns the pre-registered tie-break.  Reconcile our
    # independently recomputed totals, then use its exact ordering so the
    # optimiser cannot select a different parent merely because of a tie.
    summary_standings = [dict(item) for item in (summary.get("standings") or [])]
    if not summary_standings:
        raise ValueError("complete league summary has no standings")
    for item in summary_standings:
        item["score_rate"] = float(item["points"]) / max(1, int(item["games"]))
    recomputed_by_id = {item["model_id"]: item for item in diagnostics["standings"]}
    for official in summary_standings:
        model_id = str(official["model_id"])
        recomputed = recomputed_by_id.get(model_id)
        if recomputed is None:
            raise ValueError(f"summary model missing from recomputed diagnostics: {model_id}")
        for field in ("points", "wins", "draws", "losses", "games"):
            if not math.isclose(float(recomputed[field]), float(official[field]), abs_tol=1e-9):
                raise ValueError(f"summary/recomputed mismatch for {model_id}.{field}")
    diagnostics["standings"] = summary_standings
    diagnostics["leader"] = str(summary_standings[0]["model_id"])
    diagnostics["lowest"] = str(summary_standings[-1]["model_id"])
    diagnostics["leader_vs_lowest_total_point_gap"] = float(summary_standings[0]["points"]) - float(
        summary_standings[-1]["points"]
    )
    gap_sources = []
    leader_id, lowest_id = diagnostics["leader"], diagnostics["lowest"]
    if leader_id != lowest_id:
        opponents = sorted(
            set(diagnostics["models"][leader_id]["by_opponent"])
            | set(diagnostics["models"][lowest_id]["by_opponent"])
        )
        for opponent in opponents:
            if opponent in {leader_id, lowest_id}:
                continue
            high = diagnostics["models"][leader_id]["by_opponent"].get(opponent)
            low = diagnostics["models"][lowest_id]["by_opponent"].get(opponent)
            if high and low:
                gap_sources.append(
                    {
                        "opponent": opponent,
                        "leader_score_rate": high["score_rate"],
                        "lowest_score_rate": low["score_rate"],
                        "score_rate_gap": high["score_rate"] - low["score_rate"],
                        "mean_margin_gap": (high["mean_margin"] or 0.0)
                        - (low["mean_margin"] or 0.0),
                    }
                )
    diagnostics["leader_vs_lowest_gap_sources"] = sorted(
        gap_sources, key=lambda item: item["score_rate_gap"], reverse=True
    )
    if not diagnostics["leader"]:
        raise ValueError("cannot choose a parent from an empty ranking")
    leader = str(diagnostics["leader"])
    representatives = select_representative_losses(
        diagnostics, leader, representative_count
    )
    if len(representatives) < representative_count:
        raise ValueError(
            f"need {representative_count} unique representative loss/stress games, "
            f"got {len(representatives)}"
        )
    reruns = []
    for item in representatives:
        rerun = rerun_match(
            registry_path=registry_path,
            model_a=item["model"],
            model_b=item["opponent"],
            model_a_seat=int(item["model_seat"]),
            source=item["source"],
            data_root=data_root,
        )
        if not rerun["done"] or rerun["steps"] != 720:
            raise RuntimeError(
                f"representative rerun failed for seed {item['source'].get('seed')}"
            )
        rerun["category"] = item["category"]
        reruns.append(rerun)
    traces_path = output_dir / "representative_replays.json.gz"
    with gzip.open(traces_path, "wt", encoding="utf-8", compresslevel=9) as handle:
        json.dump(reruns, handle, ensure_ascii=False, separators=(",", ":"))
    registry, registry_specs = _registry_specs(registry_path)
    public_diagnosis = {
        key: value for key, value in diagnostics.items() if key != "perspectives"
    }
    public_diagnosis.update(
        {
            "schema": SCHEMA,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_round": int(source_round),
            "first_evaluation_round": int(source_round) + 1,
            "games_path": str(games_path),
            "games_sha256": _sha256_file(games_path),
            "summary_path": str(summary_path),
            "summary_sha256": _sha256_file(summary_path),
            "registry_path": str(registry_path),
            "registry_and_code_sha256": _load_factory().registry_fingerprint(registry),
            "sealed_test_used": False,
            "input_validation": input_validation,
            "representative_losses": representatives,
            "representative_replays_path": str(traces_path),
            "representative_replays_sha256": _sha256_file(traces_path),
            "replay_findings": _aggregate_findings(reruns),
            "representative_replay_summaries": [
                {
                    "category": str(rerun.get("category") or ""),
                    "date": rerun["official_source"]["date"],
                    "episode_id": rerun["official_source"]["episode_id"],
                    "seed": rerun["official_source"]["seed"],
                    "model_a": rerun["model_a"],
                    "model_b": rerun["model_b"],
                    "model_a_seat": rerun["model_a_seat"],
                    "first_production_difference_step": rerun["events"][
                        "first_production_difference_step"
                    ],
                    "opening_action_sha256_by_seat": rerun["events"][
                        "opening_action_sha256_by_seat"
                    ],
                    "operation_counts_by_seat": rerun["events"][
                        "operation_counts_by_seat"
                    ],
                    "product_flows_by_seat": rerun["events"][
                        "product_flows_by_seat"
                    ],
                    "action_events": len(rerun["events"]["action_events"]),
                    "market_events": len(rerun["events"]["market_events"]),
                    "farm_events": len(rerun["events"]["farm_events"]),
                    "town_events": len(rerun["events"]["town_events"]),
                }
                for rerun in reruns
            ],
            "leader_diagnostics": diagnostics["models"][leader],
        }
    )
    mutation_evidence = registered_mutation_evidence(public_diagnosis, registry_specs)
    public_diagnosis["registered_mutation_evidence"] = mutation_evidence
    selected, params, reasons = choose_mutation(public_diagnosis, registry_specs)
    parameter_candidates = build_parameter_candidates(
        leader,
        selected.name,
        params,
        registry_specs,
        mutation_evidence,
    )
    if not parameter_candidates:
        raise RuntimeError(
            f"all non-excluded catalog signatures have already been tried for parent={leader}; "
            "refuse to retry a catastrophic family or register a renamed duplicate"
        )
    smoke_sources = _smoke_sources(rows, representatives)
    attempts = []
    accepted = None
    for mutation_name, mutation_params in parameter_candidates:
        mutation = CATALOG[mutation_name]
        candidate_id = _candidate_id(source_round, leader, mutation_name)
        params_sha = _sha256_bytes(_stable_json(mutation_params).encode())[:8]
        smoke_registry = output_dir / f"smoke_registry_{mutation_name}_{params_sha}.json"
        smoke = run_admission_smoke(
            input_registry=registry_path,
            smoke_registry=smoke_registry,
            candidate_id=candidate_id,
            parent_id=leader,
            mutation_name=mutation_name,
            mutation_params=mutation_params,
            sources=smoke_sources,
            source_round=source_round,
        )
        attempt = {
            "mutation": mutation_name,
            "candidate_id": candidate_id,
            "smoke_registry": str(smoke_registry),
            "passed": smoke["passed"],
            "action_difference_steps": smoke["action_difference_steps"],
        }
        attempts.append(attempt)
        if smoke["passed"]:
            accepted = (mutation, mutation_params, candidate_id, smoke)
            break
    if accepted is None:
        raise RuntimeError(
            "no mutation produced a non-equivalent, 720-step, zero-stderr candidate"
        )
    mutation, mutation_params, candidate_id, smoke = accepted
    decision_reasons = []
    excluded = list(mutation_evidence.get("excluded_mutations") or [])
    if excluded:
        decision_reasons.append(
            "完整开发轮亲子对战将灾难性 mutation 整族排除："
            + ", ".join(excluded)
            + "。"
        )
    transfer_priority = list(mutation_evidence.get("strong_transfer_priority") or [])
    if mutation.name in transfer_priority:
        group = next(
            item
            for item in mutation_evidence["mechanism_groups"]
            if item["mutation"] == mutation.name
        )
        rates = ", ".join(
            f"{parent}={rate:.3f}"
            for parent, rate in group["lineage_score_rates"].items()
        )
        decision_reasons.append(
            f"跨谱系直接亲子证据优先 {mutation.name}：{rates}；"
            f"{group['lineage_count']} 条独立父谱系全部高于 0.5。"
        )
    decision_reasons.extend(
        reason
        for reason in reasons
        if not reason.startswith("模型池尚无 parent=")
        and not reason.startswith("当前父版本的全部目录参数")
    )
    decision_reasons.append(
        f"最终候选签名 parent={leader}、mutation={mutation.name}、"
        f"params={_stable_json(mutation_params)} 此前未注册。"
    )
    next_registry = output_dir / "registry_next.json"
    entry = _candidate_entry(
        candidate_id,
        leader,
        mutation.name,
        mutation_params,
        next_registry,
        source_round,
    )
    payload = _write_registry_payload(registry_path, next_registry, entry)
    temporary = next_registry.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, next_registry)
    emitted = _load_factory().load_registry(next_registry)
    _load_factory().create_agent(emitted, candidate_id)  # final registry load contract
    try:
        from .league import model_fingerprint
    except ImportError:  # direct-script CLI
        from league import model_fingerprint
    parent_serving_sha256 = model_fingerprint(emitted, leader)
    candidate_serving_sha256 = model_fingerprint(emitted, candidate_id)
    if candidate_serving_sha256 == parent_serving_sha256:
        raise RuntimeError("candidate serving policy is a renamed parent clone")
    smoke.update(
        {
            "admitted_registry": str(next_registry.resolve()),
            "admitted_registry_file_sha256": _sha256_file(next_registry),
            "admitted_registry_and_code_sha256": _load_factory().registry_fingerprint(
                emitted
            ),
            "candidate_serving_sha256": candidate_serving_sha256,
            "parent_serving_sha256": parent_serving_sha256,
        }
    )
    package_hash = hashlib.sha256()
    for path in (HERE / "candidate_agent.py", HERE / "mutation_catalog.py"):
        package_hash.update(path.name.encode())
        package_hash.update(path.read_bytes())
    package_hash.update(_stable_json(entry).encode())
    smoke_path = output_dir / "candidate_smoke.json"
    smoke_path.write_text(
        json.dumps(smoke, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    smoke_sha256 = _sha256_file(smoke_path)
    proposal = {
        "schema": "kaggriculture-v11-candidate-proposal-1",
        "model_id": candidate_id,
        "status": "pending",
        "admitted": True,
        "source_round": source_round,
        "first_evaluation_round": source_round + 1,
        "same_panel_performance_claim": False,
        "parent_models": [leader],
        "hypothesis": mutation.hypothesis,
        "change_scope": mutation.change_scope,
        "risk": mutation.risk,
        "mutation": {**mutation.public_record(), "params": mutation_params},
        "selection_reasons": decision_reasons,
        "selection_policy": {
            "mode": "completed-development-direct-parent-transfer",
            "excluded_mutations": excluded,
            "strong_transfer_priority": transfer_priority,
            "evidence": mutation_evidence,
        },
        "mutation_attempts": attempts,
        "registry_path": str(next_registry),
        "registry_entry": entry,
        "code_paths": [str(HERE / "candidate_agent.py"), str(HERE / "mutation_catalog.py")],
        "code_and_config_sha256": package_hash.hexdigest(),
        "diagnosis_paths": {
            "json": str(output_dir / "diagnosis.json"),
            "markdown": str(output_dir / "diagnosis.md"),
            "representative_replays": str(traces_path),
        },
        "smoke_evidence": {
            **smoke,
            "path": str(smoke_path),
            "sha256": smoke_sha256,
        },
    }
    diagnosis_path = output_dir / "diagnosis.json"
    diagnosis_path.write_text(
        json.dumps(public_diagnosis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    proposal_path = output_dir / "proposal.json"
    proposal_path.write_text(
        json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path = output_dir / "diagnosis.md"
    markdown_path.write_text(
        render_markdown(public_diagnosis, proposal), encoding="utf-8"
    )
    return {
        "diagnosis": str(diagnosis_path),
        "markdown": str(markdown_path),
        "proposal": str(proposal_path),
        "registry_next": str(next_registry),
        "candidate_id": candidate_id,
        "source_round": source_round,
        "first_evaluation_round": source_round + 1,
        "smoke_passed": True,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--round", type=int, required=True, dest="source_round")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--representative-losses", type=int, default=3)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = optimise_round(
        games_path=args.games,
        summary_path=args.summary,
        registry_path=args.registry,
        output_dir=args.output_dir,
        source_round=args.source_round,
        data_root=args.data_root,
        representative_count=args.representative_losses,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
