"""Evaluate V12A ablations on already-exposed frozen_v3/v4 screen seeds.

This utility never imports either formal panel.  It creates a development-only
registry beside its output and evaluates only explicitly named variants and
opponents.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as ev


HERE = Path(__file__).resolve().parent
VALIDATION = HERE.parent / "v12_validation"
ABLATION_MODULE = HERE / "ablation_variants.py"
PARENT = "r002_learned_router_topday_animal_throttle"
COMMON_OPPONENTS = (
    "baseline_v1",
    "baseline_v5",
    "baseline_v8",
    "learned_router",
    "rule_router",
    "v5_topdays",
    "v8_topdays",
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _variant_id(name: str) -> str:
    return f"v12a_ablate_{name}"


def _build_registry(version: str, variants: list[str], output: Path) -> Path:
    source = VALIDATION / f"frozen_{version}" / "combined_registry.json"
    registry = json.loads(source.read_text(encoding="utf-8"))
    existing = {str(item["id"]) for item in registry["models"]}
    for variant in variants:
        model_id = _variant_id(variant)
        if model_id in existing:
            continue
        registry["models"].append(
            {
                "id": model_id,
                "kind": "python",
                "path": str(ABLATION_MODULE.resolve()),
                "factory": "make_agent",
                "factory_kwargs": {"variant": variant},
                "family": "v12a-development-ablation",
                "lineage": [PARENT, "v12a_terminal_branch_guard", model_id],
                "parent_models": [PARENT],
                "tags": ["development-only", "screen-only", f"ablation:{variant}"],
                "code_paths": [
                    str(ABLATION_MODULE.resolve()),
                    str((HERE / "main.py").resolve()),
                ],
            }
        )
    registry["schema"] = "kaggriculture-v12a-development-ablation-registry-1"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def _task_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def _tasks(
    version: str,
    registry: Path,
    variants: list[str],
    opponents: list[str],
) -> list[dict[str, Any]]:
    panel = json.loads(
        (VALIDATION / f"frozen_{version}" / "screen_panel.json").read_text(encoding="utf-8")
    )["records"]
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "domain": "v12a-mechanism-ablation-screen-only-1",
                "version": version,
                "variants": variants,
                "opponents": opponents,
                "panel": panel,
                "module_sha256": hashlib.sha256(ABLATION_MODULE.read_bytes()).hexdigest(),
                "main_sha256": hashlib.sha256((HERE / "main.py").read_bytes()).hexdigest(),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    tasks: list[dict[str, Any]] = []
    for variant in variants:
        model_a = _variant_id(variant)
        for model_b in opponents:
            pair_id = f"{model_a}__vs__{model_b}"
            for source in panel:
                for seat in (0, 1):
                    identity = (
                        f"{fingerprint}:{pair_id}:{source['date']}:"
                        f"{source['seed']}:{source.get('episode_id', '')}:{seat}"
                    )
                    tasks.append(
                        {
                            "task_id": _task_id(identity),
                            "run_fingerprint": fingerprint,
                            "pair_id": pair_id,
                            "model_a": model_a,
                            "model_b": model_b,
                            "model_a_seat": seat,
                            "source": source,
                            "registry": str(registry.resolve()),
                        }
                    )
    return tasks


def _perspective(row: Mapping[str, Any], model: str) -> tuple[int, float, float]:
    if row["model_a"] == model:
        return int(row["model_a_seat"]), float(row["score_a"]), float(row["margin_a"])
    return 1 - int(row["model_a_seat"]), 1.0 - float(row["score_a"]), -float(row["margin_a"])


def _parent_controls(version: str, opponent: str) -> dict[tuple[str, int, int], tuple[float, float]]:
    control = VALIDATION / f"runs_{version}" / "screen_control"
    for path in control.glob("*/*games.jsonl"):
        rows = _read_jsonl(path)
        if not rows:
            continue
        if {rows[0]["model_a"], rows[0]["model_b"]} != {PARENT, opponent}:
            continue
        result = {}
        for row in rows:
            seat, score, margin = _perspective(row, PARENT)
            source = row["source"]
            result[(str(source["date"]), int(source["seed"]), seat)] = (score, margin)
        return result
    raise FileNotFoundError(f"missing parent control for {version}/{opponent}")


def _report(version: str, variants: list[str], opponents: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row.get("error") is None and row.get("done") is True]
    by_pair: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in valid:
        by_pair.setdefault((str(row["model_a"]), str(row["model_b"])), []).append(row)
    result: dict[str, Any] = {}
    for variant in variants:
        model = _variant_id(variant)
        per_opponent: dict[str, Any] = {}
        pooled_score_delta: list[float] = []
        pooled_margin_delta: list[float] = []
        transitions: Counter[str] = Counter()
        for opponent in opponents:
            pair_rows = by_pair.get((model, opponent), [])
            scores = [float(row["score_a"]) for row in pair_rows]
            margins = [float(row["margin_a"]) for row in pair_rows]
            item: dict[str, Any] = {
                "games": len(pair_rows),
                "score_rate": sum(scores) / len(scores) if scores else None,
                "mean_margin": sum(margins) / len(margins) if margins else None,
            }
            if opponent != PARENT:
                controls = _parent_controls(version, opponent)
                score_delta: list[float] = []
                margin_delta: list[float] = []
                local_transitions: Counter[str] = Counter()
                for row in pair_rows:
                    source = row["source"]
                    key = (str(source["date"]), int(source["seed"]), int(row["model_a_seat"]))
                    parent_score, parent_margin = controls[key]
                    candidate_score = float(row["score_a"])
                    score_delta.append(candidate_score - parent_score)
                    margin_delta.append(float(row["margin_a"]) - parent_margin)
                    label = f"{parent_score:g}->{candidate_score:g}"
                    local_transitions[label] += 1
                    transitions[label] += 1
                pooled_score_delta.extend(score_delta)
                pooled_margin_delta.extend(margin_delta)
                item.update(
                    {
                        "score_uplift_vs_parent": sum(score_delta) / len(score_delta),
                        "margin_uplift_vs_parent": sum(margin_delta) / len(margin_delta),
                        "transitions": dict(sorted(local_transitions.items())),
                    }
                )
            per_opponent[opponent] = item
        result[variant] = {
            "direct_parent": per_opponent.get(PARENT),
            "common_score_uplift": sum(pooled_score_delta) / len(pooled_score_delta),
            "common_margin_uplift": sum(pooled_margin_delta) / len(pooled_margin_delta),
            "worst_opponent_score_uplift": min(
                value["score_uplift_vs_parent"]
                for key, value in per_opponent.items()
                if key != PARENT
            ),
            "transitions": dict(sorted(transitions.items())),
            "per_opponent": per_opponent,
        }
    return {
        "schema": "kaggriculture-v12a-mechanism-ablation-report-1",
        "screen_only": True,
        "formal_or_test_accessed": False,
        "version": version,
        "variants": variants,
        "opponents": opponents,
        "valid_games": len(valid),
        "errors": len(rows) - len(valid),
        "results": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=("v3", "v4"), required=True)
    parser.add_argument("--variants", nargs="+", required=True)
    parser.add_argument("--opponents", nargs="+", default=[PARENT, *COMMON_OPPONENTS])
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--run-name",
        default="default",
        help="development output subdirectory; does not affect the panel",
    )
    args = parser.parse_args()
    output = HERE / "mechanism_ablation" / args.run_name / args.version
    registry = _build_registry(args.version, args.variants, output / "registry.json")
    tasks = _tasks(args.version, registry, args.variants, args.opponents)
    rows = ev.run_tasks(tasks, output / "games.jsonl", args.workers, args.resume)
    current_ids = {str(task["task_id"]) for task in tasks}
    rows = [row for row in rows if str(row.get("task_id")) in current_ids]
    report = _report(args.version, args.variants, args.opponents, rows)
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
