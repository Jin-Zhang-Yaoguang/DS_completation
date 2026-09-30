"""Evaluate V12C only on the already-exposed frozen_v3 18-seed screen."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from typing import Any, Mapping

import numpy as np

from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as pe
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    load_registry,
    registry_fingerprint,
)


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
V12 = MODEL_ROOT / "v12_validation"
FROZEN = V12 / "frozen_v3"
RUNS = HERE / "screen_runs"
CLEAN = HERE / "screen_clean_package"
REGISTRY = HERE / "screen_registry.json"
REPORT = HERE / "screen_report.json"
CANDIDATE = "v12c_yarn_complete_router"
PARENT = "baseline_v8"
OPPONENTS = (
    "baseline_v1",
    "baseline_v5",
    "learned_router",
    "r002_learned_router_topday_animal_throttle",
    "rule_router",
    "v5_topdays",
    "v8_topdays",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _prepare_registry() -> Any:
    if CLEAN.exists():
        shutil.rmtree(CLEAN)
    CLEAN.mkdir(parents=True)
    with tarfile.open(HERE / "submission.tar.gz", "r:gz") as archive:
        archive.extractall(CLEAN, filter="data")
    payload = json.loads(
        (FROZEN / "combined_registry.json").read_text(encoding="utf-8")
    )
    payload["models"] = [
        item for item in payload["models"] if item.get("id") != CANDIDATE
    ]
    code_paths = [
        str(path.resolve())
        for path in sorted(CLEAN.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    ]
    payload["models"].append(
        {
            "id": CANDIDATE,
            "kind": "python",
            "path": str((CLEAN / "main.py").resolve()),
            "factory": "make_agent",
            "code_paths": code_paths,
            "family": "observable_yarn_complete_expert_router",
            "lineage": ["baseline_v5", "baseline_v8", CANDIDATE],
            "tags": ["complete-expert-router", "observed-yarn-store"],
            "validation_runtime": "clean_submission_archive",
        }
    )
    REGISTRY.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return load_registry(REGISTRY)


def _screen_panel() -> list[pe.SeedRecord]:
    panel_payload = json.loads(
        (FROZEN / "screen_panel.json").read_text(encoding="utf-8")
    )
    if int(panel_payload.get("count", 0)) != 18:
        raise ValueError("expected the already-exposed 18-seed screen")
    if any(str(row.get("split")) == "test" for row in panel_payload["records"]):
        raise ValueError("screen unexpectedly contains test sources")
    return [pe.SeedRecord(**row) for row in panel_payload["records"]]


def _task_id(fingerprint: str, pair: str, source: pe.SeedRecord, seat: int) -> str:
    raw = (
        f"{fingerprint}:{pair}:{source.date}:{source.episode_id}:"
        f"{source.seed}:candidate-seat-{seat}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _tasks(registry: Any, panel: list[pe.SeedRecord]) -> tuple[str, list[dict[str, Any]]]:
    models = [CANDIDATE, PARENT, *OPPONENTS]
    fingerprint_payload = {
        "schema": "kaggriculture-v12c-exposed-screen-1",
        "evaluator": pe.implementation_fingerprint(),
        "registry": registry_fingerprint(registry),
        "models": models,
        "candidate_pairs_only": True,
        "panel": [asdict(row) for row in panel],
    }
    fingerprint = hashlib.sha256(_canonical(fingerprint_payload)).hexdigest()
    tasks: list[dict[str, Any]] = []
    for opponent in [PARENT, *OPPONENTS]:
        pair = f"{CANDIDATE}__vs__{opponent}"
        for source in panel:
            for seat in (0, 1):
                tasks.append(
                    {
                        "task_id": _task_id(fingerprint, pair, source, seat),
                        "run_fingerprint": fingerprint,
                        "pair_id": pair,
                        "model_a": CANDIDATE,
                        "model_b": opponent,
                        "model_a_seat": seat,
                        "source": asdict(source),
                        "registry": str(REGISTRY.resolve()),
                    }
                )
    return fingerprint, tasks


def _context(row: Mapping[str, Any], model: str, opponent: str) -> tuple[Any, ...]:
    source = row["source"]
    if row["model_a"] == model:
        seat = int(row["model_a_seat"])
    else:
        seat = 1 - int(row["model_a_seat"])
    return (str(source["date"]), int(source["seed"]), seat, opponent)


def _model_score(row: Mapping[str, Any], model: str) -> tuple[float, float]:
    if row["model_a"] == model:
        return float(row["score_a"]), float(row["margin_a"])
    return 1.0 - float(row["score_a"]), -float(row["margin_a"])


def _control_rows(opponent: str) -> list[dict[str, Any]]:
    control = V12 / "runs_v3" / "screen_control"
    candidates = [
        control / f"{PARENT}__vs__{opponent}" / "games.jsonl",
        control / f"{opponent}__vs__{PARENT}" / "games.jsonl",
    ]
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        raise FileNotFoundError(f"missing exposed parent control for {opponent}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _cluster_ci(values: Mapping[tuple[str, int], list[float]], seed: int) -> list[float]:
    keys = sorted(values)
    array = np.asarray([np.mean(values[key]) for key in keys], dtype=np.float64)
    rng = np.random.default_rng(seed)
    samples = np.empty(5000, dtype=np.float64)
    for start in range(0, 5000, 500):
        index = rng.integers(0, len(array), size=(min(500, 5000 - start), len(array)))
        samples[start : start + len(index)] = array[index].mean(axis=1)
    return [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]


def evaluate(workers: int = 12) -> dict[str, Any]:
    registry = _prepare_registry()
    panel = _screen_panel()
    fingerprint, tasks = _tasks(registry, panel)
    rows = pe.run_tasks(tasks, RUNS / "games.jsonl", workers, resume=False)
    valid = [
        row
        for row in rows
        if row.get("run_fingerprint") == fingerprint
        and row.get("error") is None
        and row.get("done") is True
    ]
    if len(valid) != len(tasks):
        raise RuntimeError({"scheduled": len(tasks), "valid": len(valid)})

    direct = [row for row in valid if row["model_b"] == PARENT]
    direct_scores = [float(row["score_a"]) for row in direct]
    direct_margins = [float(row["margin_a"]) for row in direct]

    candidate_by_context: dict[tuple[Any, ...], tuple[float, float]] = {}
    trigger_counts: Counter[str] = Counter()
    selection_by_source: dict[tuple[str, int, int], str] = {}
    for row in valid:
        opponent = str(row["model_b"])
        candidate_by_context[_context(row, CANDIDATE, opponent)] = _model_score(
            row, CANDIDATE
        )
        diagnostics = row["agent_diagnostics"][CANDIDATE]["underlying"]
        selected = str(diagnostics.get("selected"))
        trigger_counts[selected] += 1
        key = (
            str(row["source"]["date"]),
            int(row["source"]["seed"]),
            int(row["model_a_seat"]),
        )
        old = selection_by_source.setdefault(key, selected)
        if old != selected:
            raise RuntimeError("candidate selection changed with opponent on common opening")
        if diagnostics.get("runtime_errors") or diagnostics.get("selected_fallbacks"):
            raise RuntimeError(diagnostics)
        if not diagnostics.get("prefix_complete") or not diagnostics.get("prefix_match"):
            raise RuntimeError(diagnostics)

    paired: list[dict[str, Any]] = []
    for opponent in OPPONENTS:
        for row in _control_rows(opponent):
            if row.get("error") is not None or not row.get("done"):
                continue
            key = _context(row, PARENT, opponent)
            candidate = candidate_by_context[key]
            parent = _model_score(row, PARENT)
            paired.append(
                {
                    "date": key[0],
                    "seed": key[1],
                    "seat": key[2],
                    "opponent": opponent,
                    "candidate_score": candidate[0],
                    "parent_score": parent[0],
                    "score_uplift": candidate[0] - parent[0],
                    "margin_uplift": candidate[1] - parent[1],
                }
            )
    if len(paired) != len(OPPONENTS) * len(panel) * 2:
        raise RuntimeError({"paired": len(paired)})

    clusters: dict[tuple[str, int], list[float]] = defaultdict(list)
    for row in paired:
        clusters[(row["date"], row["seed"])].append(row["score_uplift"])
    by_opponent = {}
    for opponent in OPPONENTS:
        subset = [row for row in paired if row["opponent"] == opponent]
        by_opponent[opponent] = {
            "games": len(subset),
            "score_uplift": float(np.mean([row["score_uplift"] for row in subset])),
            "margin_uplift": float(np.mean([row["margin_uplift"] for row in subset])),
            "transitions": dict(
                Counter(
                    f"{row['parent_score']:g}->{row['candidate_score']:g}"
                    for row in subset
                )
            ),
        }

    aggregate_uplift = float(np.mean([row["score_uplift"] for row in paired]))
    worst = min(value["score_uplift"] for value in by_opponent.values())
    report = {
        "schema": "kaggriculture-v12c-exposed-screen-report-1",
        "epistemic_status": "development screen only; formal panel not accessed",
        "formal_panel_accessed": False,
        "candidate": CANDIDATE,
        "parent": PARENT,
        "archive_sha256": _sha256(HERE / "submission.tar.gz"),
        "clean_registry_and_code_sha256": registry_fingerprint(registry),
        "screen_panel_records_sha256": json.loads(
            (FROZEN / "screen_panel.json").read_text(encoding="utf-8")
        )["records_sha256"],
        "sources": len(panel),
        "scheduled_games": len(tasks),
        "valid_games": len(valid),
        "direct_parent": {
            "games": len(direct),
            "wins": sum(value == 1.0 for value in direct_scores),
            "ties": sum(value == 0.5 for value in direct_scores),
            "losses": sum(value == 0.0 for value in direct_scores),
            "score_rate": float(np.mean(direct_scores)),
            "mean_margin": float(np.mean(direct_margins)),
        },
        "common_opponent_paired": {
            "games": len(paired),
            "score_uplift": aggregate_uplift,
            "score_uplift_ci95_source_cluster": _cluster_ci(clusters, 20260823),
            "margin_uplift": float(np.mean([row["margin_uplift"] for row in paired])),
            "worst_opponent_score_uplift": worst,
            "transitions": dict(
                Counter(
                    f"{row['parent_score']:g}->{row['candidate_score']:g}"
                    for row in paired
                )
            ),
            "by_opponent": by_opponent,
        },
        "selection_source_seats": dict(Counter(selection_by_source.values())),
        "selection_game_calls": dict(trigger_counts),
        "gates": {
            "all_games_valid": len(valid) == len(tasks),
            "direct_parent_point_at_least_half": float(np.mean(direct_scores)) >= 0.5,
            "aggregate_score_uplift_positive": aggregate_uplift > 0.0,
            "worst_opponent_no_regression": worst >= 0.0,
            "formal_panel_untouched": True,
        },
    }
    report["screen_passed"] = all(report["gates"].values())
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":
    evaluate()

