"""Reproducible, shard-safe D2 collection orchestrator for PPO v3.

This program deliberately composes the existing ``collect_states`` and
``fork_counterfactuals`` primitives instead of duplicating their simulator
logic.  Its job is operational:

* collect one contiguous source rollout per seed chunk and retain only the
  configured decision days;
* keep production-route observations at the day-3 commitment point while
  sampling market residuals at several daily points;
* submit disjoint, contiguous state-index ranges to D2 workers;
* reject duplicate replay recipes before the expensive branches begin; and
* produce a manifest and a coverage report which make a training input
  inspectable without opening opaque NPZ files.

The output directory is treated as an immutable run directory.  ``--resume``
only reuses a task when its recorded input fingerprint still matches.  This
prevents a changed config or source state file from quietly mixing into an
older D2 dataset.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import shutil
import sys
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from collect_states import (
    DEFAULT_MARKET,
    DEFAULT_PRODUCTION,
    SCHEMA_VERSION_STATES,
    canonical_json,
    collect_states,
    split_for_group,
)
from fork_counterfactuals import SCHEMA_VERSION_CF, fork_counterfactuals
from merge_d2_shards import merge


ORCHESTRATOR_SCHEMA = "kaggriculture-ppo-v3-d2-orchestrator-1"
DEFAULT_CONFIG: dict[str, Any] = {
    "schema": ORCHESTRATOR_SCHEMA,
    "seed_start": 97300000,
    "seed_count": 16,
    "seed_stride": 7919,
    "opponents": ["starter", "forced_low", "forced_high", "v1"],
    "source_expert": "E_V1",
    "production_days": [3],
    "market_days": [3, 5, 7, 10, 14, 18, 22, 26],
    "production": ["E_V1"],
    "market": ["M_NONE", "M_ANIMAL_HALF_TOPDAYS"],
    "market_horizon_days": 1,
    "state_shards": 4,
    "fork_shards": 8,
    "workers": 4,
    "min_coverage": {
        "total_states": 1,
        "per_split": {"train": 1, "validation": 0, "test": 0},
        "effective_production": {},
        "effective_market": {"M_ANIMAL_HALF_TOPDAYS": 1},
    },
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("config must be a JSON object")
    return payload


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _normalise_config(raw: Mapping[str, Any]) -> dict[str, Any]:
    config = _deep_merge(DEFAULT_CONFIG, raw)
    # A run's coverage gate is a contract, not a set of optional defaults.
    # In particular, a small smoke that asks only for one market residual must not
    # silently inherit requirements for experts it did not collect.
    if "min_coverage" in raw:
        config["min_coverage"] = dict(raw["min_coverage"] or {})
    if config.get("schema") != ORCHESTRATOR_SCHEMA:
        raise ValueError("unsupported config schema: %r" % (config.get("schema"),))
    if "seeds" in raw:
        seeds = [int(value) for value in raw["seeds"]]
    else:
        count, start, stride = int(config["seed_count"]), int(config["seed_start"]), int(config["seed_stride"])
        if count < 1 or stride < 1:
            raise ValueError("seed_count and seed_stride must be positive")
        seeds = [start + stride * index for index in range(count)]
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be non-empty and unique")
    config["seeds"] = seeds
    config["opponents"] = [str(value) for value in config["opponents"]]
    if not config["opponents"] or len(set(config["opponents"])) != len(config["opponents"]):
        raise ValueError("opponents must be non-empty and unique")
    config["production"] = [str(value) for value in config["production"]]
    config["market"] = [str(value) for value in config["market"]]
    if set(config["production"]) - set(DEFAULT_PRODUCTION) or "E_V1" not in config["production"]:
        raise ValueError("production must contain registered E_V1 anchor")
    if set(config["market"]) - set(DEFAULT_MARKET) or "M_NONE" not in config["market"]:
        raise ValueError("market must contain registered M_NONE anchor")
    if str(config["source_expert"]) != "E_V1":
        raise ValueError("D2 source_expert must be E_V1 so every label uses the same anchor prefix")
    production_days = sorted({int(day) for day in config["production_days"]})
    market_days = sorted({int(day) for day in config["market_days"]})
    if production_days != [3]:
        raise ValueError("production_days must be exactly [3]: the production route is committed at day 3")
    if not market_days or any(day < 3 or day > 29 for day in market_days):
        raise ValueError("market_days must be non-empty daily points in [3, 29]")
    config["production_days"], config["market_days"] = production_days, market_days
    config["sample_days"] = sorted(set(production_days + market_days))
    for key in ("state_shards", "fork_shards", "workers"):
        config[key] = int(config[key])
        if config[key] < 1:
            raise ValueError("%s must be positive" % key)
    config["market_horizon_days"] = int(config["market_horizon_days"])
    if not 1 <= config["market_horizon_days"] <= 7:
        raise ValueError("market_horizon_days must be 1..7")
    config["min_coverage"] = dict(config.get("min_coverage") or {})
    return config


def _chunks(values: list[int], count: int) -> list[list[int]]:
    count = min(max(1, int(count)), len(values))
    width = int(math.ceil(len(values) / count))
    return [values[index:index + width] for index in range(0, len(values), width)]


def _recipe_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(name) for name in ("source_expert", "opponent_id", "seed", "seat", "step"))


def _task_fingerprint(kind: str, payload: Mapping[str, Any]) -> str:
    return _sha256_bytes(canonical_json({"kind": kind, "payload": payload}).encode("utf-8"))


def _completed_task(path: Path, fingerprint: str, required: Iterable[Path]) -> bool:
    if not path.exists() or not all(item.exists() for item in required):
        return False
    try:
        return _load_json(path).get("fingerprint") == fingerprint
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _run_state_task(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Worker: one disjoint seed chunk, retaining selected days only."""
    output_dir = Path(str(payload["output_dir"]))
    raw_dir = output_dir / "raw_collect"
    report = collect_states(
        seeds=[int(seed) for seed in payload["seeds"]],
        opponents=[str(value) for value in payload["opponents"]],
        output_dir=raw_dir,
        source_expert=str(payload["source_expert"]),
        start_day=int(payload["start_day"]),
        end_day=int(payload["end_day"]),
    )
    selected = set(int(day) for day in payload["sample_days"])
    raw_rows = [
        json.loads(line) for line in (raw_dir / "daily_states.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    retained = [row for row in raw_rows if int(row["day"]) in selected]
    retained.sort(key=lambda row: (row["seed"], row["seat"], row["step"], row["state_id"]))
    rows_path = output_dir / "selected_states.jsonl"
    rows_path.write_text("".join(canonical_json(row) + "\n" for row in retained), encoding="utf-8")
    worker_report = {
        "schema": ORCHESTRATOR_SCHEMA,
        "task": "collect_states",
        "fingerprint": str(payload["fingerprint"]),
        "input": dict(payload),
        "core_report": report,
        "raw_rows": len(raw_rows),
        "retained_rows": len(retained),
        "retained_by_day": {str(day): sum(int(row["day"]) == day for row in retained) for day in sorted(selected)},
        "selected_states_sha256": _sha256_file(rows_path),
    }
    _json_dump(output_dir / "task_manifest.json", worker_report)
    return worker_report


def _run_fork_task(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Worker: one non-overlapping contiguous slice of globally sorted states."""
    output_dir = Path(str(payload["output_dir"]))
    report = fork_counterfactuals(
        states_file=Path(str(payload["states_file"])),
        output_dir=output_dir,
        production_ids=payload["production"],
        market_ids=payload["market"],
        horizon_days=int(payload["market_horizon_days"]),
        start_index=int(payload["start_index"]),
        max_states=int(payload["max_states"]),
    )
    worker_report = {
        "schema": ORCHESTRATOR_SCHEMA,
        "task": "fork_counterfactuals",
        "fingerprint": str(payload["fingerprint"]),
        "input": dict(payload),
        "core_report": report,
        "dataset_sha256": _sha256_file(output_dir / "d2_counterfactual.npz"),
        "rows_sha256": _sha256_file(output_dir / "counterfactual_rows.jsonl"),
    }
    _json_dump(output_dir / "task_manifest.json", worker_report)
    return worker_report


def _submit_tasks(
    *,
    tasks: list[dict[str, Any]],
    worker,
    workers: int,
    phase: str,
) -> list[dict[str, Any]]:
    if not tasks:
        return []
    reports: list[dict[str, Any]] = []
    # Separate simulator processes avoid shared mutable Kaggle environment and
    # module-level agent state.  Each task owns a distinct output directory.
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(int(workers), len(tasks))) as executor:
        future_map = {executor.submit(worker, task): task for task in tasks}
        for completed, future in enumerate(concurrent.futures.as_completed(future_map), 1):
            task = future_map[future]
            try:
                report = future.result()
            except BaseException as exc:
                raise RuntimeError(
                    "%s task failed for %s:\n%s" % (phase, task.get("output_dir"), traceback.format_exc())
                ) from exc
            reports.append(report)
            print(json.dumps({"phase": phase, "completed": completed, "total": len(tasks), "output": task["output_dir"]}), flush=True)
    return reports


def _merge_state_rows(state_task_dirs: list[Path], output_dir: Path, config: Mapping[str, Any]) -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    seen_state_ids: set[str] = set()
    seen_recipes: set[tuple[Any, ...]] = set()
    for directory in state_task_dirs:
        path = directory / "selected_states.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("schema") != SCHEMA_VERSION_STATES:
                raise ValueError("%s: unexpected state schema" % path)
            if str(row["state_id"]) in seen_state_ids:
                raise ValueError("duplicate state_id across collection tasks: %s" % row["state_id"])
            recipe = _recipe_key(row)
            if recipe in seen_recipes:
                raise ValueError("duplicate replay recipe across collection tasks: %r" % (recipe,))
            expected_split = split_for_group(str(row["split_group"]))
            if row.get("split") != expected_split:
                raise ValueError("split contract mismatch for %s" % row["state_id"])
            seen_state_ids.add(str(row["state_id"]))
            seen_recipes.add(recipe)
            all_rows.append(row)
    all_rows.sort(key=lambda row: (row["seed"], row["seat"], row["step"], row["state_id"]))
    if not all_rows:
        raise ValueError("no daily states survived configured sampling days")
    merged = output_dir / "daily_states.jsonl"
    merged.write_text("".join(canonical_json(row) + "\n" for row in all_rows), encoding="utf-8")
    report = {
        "schema": ORCHESTRATOR_SCHEMA,
        "states": len(all_rows),
        "days": {str(day): sum(int(row["day"]) == day for row in all_rows) for day in config["sample_days"]},
        "splits": {name: sum(row["split"] == name for row in all_rows) for name in ("train", "validation", "test")},
        "state_ids_unique": len(seen_state_ids) == len(all_rows),
        "replay_recipes_unique": len(seen_recipes) == len(all_rows),
        "sha256": _sha256_file(merged),
        "file": str(merged),
    }
    _json_dump(output_dir / "state_merge_manifest.json", report)
    return report


def _counter(values: Iterable[Any]) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(Counter(values).items(), key=lambda item: str(item[0]))}


def _coverage(dataset: Path, state_merge: Mapping[str, Any], config: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    with np.load(dataset, allow_pickle=False) as data:
        features = np.asarray(data["features"])
        production_names = [str(value) for value in data["production_names"].tolist()]
        market_names = [str(value) for value in data["market_names"].tolist()]
        production_mask = np.asarray(data["production_mask"], dtype=bool)
        market_mask = np.asarray(data["market_mask"], dtype=bool)
        p_uplift = np.asarray(data["production_uplift"], dtype=float)
        m_uplift = np.asarray(data["market_uplift"], dtype=float)
        effective = np.asarray(data["effective_action_change"], dtype=bool)
        splits = [str(value) for value in data["split"].tolist()]
        days = [int(value) for value in data["day"].tolist()] if "day" in data.files else []
        families = [str(value) for value in data["family"].tolist()]
        opponents = [str(value) for value in data["opponent_id"].tolist()] if "opponent_id" in data.files else []
        seats = [int(value) for value in data["seat"].tolist()]
        state_ids = [str(value) for value in data["state_ids"].tolist()]
    if len(set(state_ids)) != len(state_ids):
        raise ValueError("merged D2 dataset contains duplicate state_ids")
    if not np.isfinite(features).all():
        raise ValueError("merged D2 dataset contains non-finite features")
    v1_index, none_index = production_names.index("E_V1"), market_names.index("M_NONE")
    p_actions: dict[str, dict[str, int]] = {}
    for index, name in enumerate(production_names):
        labeled = production_mask[:, index] & np.isfinite(p_uplift[:, index])
        changed = effective[:, index, none_index] if index != v1_index else np.zeros(len(features), dtype=bool)
        p_actions[name] = {
            "labeled": int(labeled.sum()),
            "effective": int((labeled & changed).sum()),
            "positive_uplift": int((labeled & (p_uplift[:, index] > 0)).sum()),
            "negative_uplift": int((labeled & (p_uplift[:, index] < 0)).sum()),
        }
    m_actions: dict[str, dict[str, int]] = {}
    for index, name in enumerate(market_names):
        labeled = market_mask[:, index] & np.isfinite(m_uplift[:, index])
        changed = effective[:, v1_index, index] if index != none_index else np.zeros(len(features), dtype=bool)
        m_actions[name] = {
            "labeled": int(labeled.sum()),
            "effective": int((labeled & changed).sum()),
            "positive_uplift": int((labeled & (m_uplift[:, index] > 0)).sum()),
            "negative_uplift": int((labeled & (m_uplift[:, index] < 0)).sum()),
        }
    coverage = {
        "schema": ORCHESTRATOR_SCHEMA,
        "dataset": str(dataset),
        "dataset_sha256": _sha256_file(dataset),
        "rows": int(len(features)),
        "feature_dim": int(features.shape[1]),
        "state_ids_unique": True,
        "features_finite": True,
        "source_state_merge": dict(state_merge),
        "by_split": _counter(splits),
        "by_day": _counter(days),
        "by_family": _counter(families),
        "by_opponent": _counter(opponents),
        "by_seat": _counter(seats),
        "production_actions": p_actions,
        "market_actions": m_actions,
    }
    minimum = config["min_coverage"]
    split_min = dict(minimum.get("per_split") or {})
    missing_split = {key: int(value) for key, value in split_min.items() if coverage["by_split"].get(key, 0) < int(value)}
    missing_prod = {
        key: int(value) for key, value in dict(minimum.get("effective_production") or {}).items()
        if p_actions.get(key, {}).get("effective", 0) < int(value)
    }
    missing_market = {
        key: int(value) for key, value in dict(minimum.get("effective_market") or {}).items()
        if m_actions.get(key, {}).get("effective", 0) < int(value)
    }
    coverage["acceptance"] = {
        "minimum_total_states": int(len(features)) >= int(minimum.get("total_states", 0)),
        "split_coverage": not missing_split,
        "effective_production_coverage": not missing_prod,
        "effective_market_coverage": not missing_market,
        "missing": {"splits": missing_split, "production": missing_prod, "market": missing_market},
    }
    coverage["acceptance"]["passed"] = all(
        value for key, value in coverage["acceptance"].items() if key not in {"missing", "passed"}
    )
    _json_dump(output_dir / "coverage.json", coverage)
    return coverage


def orchestrate(config: Mapping[str, Any], output_dir: Path, *, resume: bool = False) -> dict[str, Any]:
    config = _normalise_config(config)
    output_dir = Path(output_dir).resolve()
    if output_dir.exists() and not resume:
        # A nonempty run directory can only be replaced deliberately.  It is
        # far safer to choose a new run id than merge in-place accidentally.
        if any(output_dir.iterdir()):
            raise FileExistsError("output exists; pass --resume after checking its manifest, or use a new --output-dir")
    output_dir.mkdir(parents=True, exist_ok=True)
    config_digest = _sha256_bytes(canonical_json(config).encode("utf-8"))
    _json_dump(output_dir / "config.resolved.json", config)
    state_root, fork_root, logs_root = output_dir / "state_shards", output_dir / "fork_shards", output_dir / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)

    state_plan: list[dict[str, Any]] = []
    state_tasks: list[dict[str, Any]] = []
    for shard_index, seeds in enumerate(_chunks(config["seeds"], config["state_shards"])):
        task_dir = state_root / ("state_%03d" % shard_index)
        payload: dict[str, Any] = {
            "output_dir": str(task_dir), "seeds": seeds, "opponents": config["opponents"],
            "source_expert": config["source_expert"], "start_day": min(config["sample_days"]),
            "end_day": max(config["sample_days"]), "sample_days": config["sample_days"],
        }
        payload["fingerprint"] = _task_fingerprint("collect_states", payload)
        state_plan.append(payload)
        required = [task_dir / "selected_states.jsonl"]
        if resume and _completed_task(task_dir / "task_manifest.json", payload["fingerprint"], required):
            continue
        if task_dir.exists():
            shutil.rmtree(task_dir)
        state_tasks.append(payload)
    _submit_tasks(tasks=state_tasks, worker=_run_state_task, workers=config["workers"], phase="states")

    state_dirs = [Path(str(payload["output_dir"])) for payload in state_plan]
    for payload, directory in zip(state_plan, state_dirs):
        if not _completed_task(directory / "task_manifest.json", str(payload["fingerprint"]), [directory / "selected_states.jsonl"]):
            raise RuntimeError("state shard did not finish with its current fingerprint: %s" % directory)
    state_merge = _merge_state_rows(state_dirs, output_dir, config)
    states_file = output_dir / "daily_states.jsonl"
    rows_count = int(state_merge["states"])

    fork_plan: list[dict[str, Any]] = []
    fork_tasks: list[dict[str, Any]] = []
    actual_fork_shards = min(config["fork_shards"], rows_count)
    for shard_index, start in enumerate(range(0, rows_count, int(math.ceil(rows_count / actual_fork_shards)))):
        maximum = min(int(math.ceil(rows_count / actual_fork_shards)), rows_count - start)
        task_dir = fork_root / ("fork_%03d" % shard_index)
        payload = {
            "output_dir": str(task_dir), "states_file": str(states_file), "states_sha256": state_merge["sha256"],
            "start_index": start, "max_states": maximum, "production": config["production"],
            "market": config["market"], "market_horizon_days": config["market_horizon_days"],
        }
        payload["fingerprint"] = _task_fingerprint("fork_counterfactuals", payload)
        fork_plan.append(payload)
        required = [task_dir / "d2_counterfactual.npz", task_dir / "counterfactual_rows.jsonl"]
        if resume and _completed_task(task_dir / "task_manifest.json", payload["fingerprint"], required):
            continue
        if task_dir.exists():
            shutil.rmtree(task_dir)
        fork_tasks.append(payload)
    _submit_tasks(tasks=fork_tasks, worker=_run_fork_task, workers=config["workers"], phase="fork")
    fork_dirs = [Path(str(payload["output_dir"])) for payload in fork_plan]
    for payload, directory in zip(fork_plan, fork_dirs):
        if not _completed_task(
            directory / "task_manifest.json", str(payload["fingerprint"]),
            [directory / "d2_counterfactual.npz", directory / "counterfactual_rows.jsonl"],
        ):
            raise RuntimeError("fork shard did not finish with its current fingerprint: %s" % directory)
    shard_paths = [path / "d2_counterfactual.npz" for path in fork_dirs]
    merged_dataset = output_dir / "d2_counterfactual.npz"
    merge_report = merge(shard_paths, merged_dataset)
    coverage = _coverage(merged_dataset, state_merge, config, output_dir)
    report = {
        "schema": ORCHESTRATOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": {"python": sys.version.split()[0], "pid": os.getpid()},
        "config_sha256": config_digest,
        "config": config,
        "state_merge": state_merge,
        "d2_merge": merge_report,
        "coverage": coverage,
        "files": {
            "states": {"path": str(states_file), "sha256": _sha256_file(states_file)},
            "dataset": {"path": str(merged_dataset), "sha256": _sha256_file(merged_dataset)},
            "coverage": "coverage.json",
        },
        "acceptance": coverage["acceptance"],
        "note": "A failed coverage gate is a valid generated dataset but must not enter Router fitting until coverage is expanded.",
    }
    _json_dump(output_dir / "manifest.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="JSON config; omitted means write/run the documented small default")
    parser.add_argument("--output-dir", type=Path, help="immutable run directory")
    parser.add_argument("--resume", action="store_true", help="reuse only fingerprint-matching completed task shards")
    parser.add_argument("--write-example-config", type=Path, help="write the default JSON config and exit")
    args = parser.parse_args()
    if args.write_example_config:
        _json_dump(args.write_example_config, DEFAULT_CONFIG)
        print(args.write_example_config)
        return
    if args.output_dir is None:
        parser.error("--output-dir is required unless --write-example-config is used")
    raw = _load_json(args.config) if args.config else dict(DEFAULT_CONFIG)
    report = orchestrate(raw, args.output_dir, resume=args.resume)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
