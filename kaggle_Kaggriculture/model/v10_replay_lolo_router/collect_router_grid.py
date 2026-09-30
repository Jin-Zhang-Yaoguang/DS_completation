#!/usr/bin/env python3
"""Collect a paired potential-outcome grid for the step-72 expert router.

For every source seed, router seat and opponent root lineage, each candidate is
evaluated from the same anchor-generated prefix.  Candidate agents are called
in shadow mode during steps 0..71 so their episode state is current, but only
the anchor action reaches the environment.  At step 72 the public feature
vector is captured and the candidate takes over the complete remaining route.

This is closed-loop evaluation.  Official replay files supply seeds and split
labels only; historical actions are never replayed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

try:
    from .agent_factory import create_agent, load_registry, registry_fingerprint
    from .router import FEATURE_DIM, FEATURE_NAMES, FEATURE_SCHEMA, public_features
except ImportError:  # direct-file CLI compatibility
    from agent_factory import create_agent, load_registry, registry_fingerprint
    from router import FEATURE_DIM, FEATURE_NAMES, FEATURE_SCHEMA, public_features


HERE = Path(__file__).resolve().parent
GRID_SCHEMA = "kaggriculture-v10-router-outcome-grid-1"
GRID_SUMMARY_SCHEMA = "kaggriculture-v10-router-grid-summary-1"
DEFAULT_MODELS = ("baseline_v1", "baseline_v2", "baseline_v5", "baseline_v8")
DEFAULT_DATES = ("2026-08-18", "2026-08-19", "2026-08-20")
DEFAULT_REGISTRY = HERE / "router_training_registry.json"
DEFAULT_SEED_MANIFEST = HERE / "evaluation_seed_manifest.jsonl"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def collector_implementation_fingerprint() -> dict[str, str]:
    """Fingerprint collection semantics separately from serving code."""

    paths = (HERE / "collect_router_grid.py", HERE / "agent_factory.py", HERE / "router.py")
    return {path.name: _file_sha256(path) for path in paths}


def implementation_fingerprint() -> str:
    """Hash the counterfactual collector and runtime used by resume."""

    import kaggle_environments

    digest = hashlib.sha256()
    runtime = {
        "python": list(sys.version_info[:2]),
        "kaggle_environments": getattr(kaggle_environments, "__version__", "unknown"),
        "numpy": np.__version__,
    }
    digest.update(_canonical_json(runtime).encode("utf-8"))
    for path in (Path(__file__).resolve(), HERE / "agent_factory.py", HERE / "router.py"):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


@dataclass(frozen=True)
class SeedSource:
    date: str
    seed: int
    episode_id: str
    split: str
    source_relpath: str = ""


def _normalise_split(value: str) -> str:
    value = str(value).strip().lower()
    return "validation" if value in {"val", "valid", "validation"} else value


def _stable_int(text: str, modulo: int = 2**31 - 1) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big") % modulo


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _copy_action(action: Any) -> dict[str, Any]:
    if not isinstance(action, Mapping):
        raise TypeError("agent action is not a mapping")
    farmer = action.get("farmer") or ["PASS"]
    hands = action.get("hands") or []
    market = action.get("market") or []
    return {
        "farmer": list(farmer),
        "hands": [list(item or ["PASS"]) for item in hands],
        "market": [list(item or []) for item in market],
    }


def load_seed_sources(path: str | Path) -> list[SeedSource]:
    """Read the canonical flat JSONL or the structured JSON seed manifest."""

    path = Path(path).expanduser().resolve()
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, Mapping) and isinstance(payload.get("splits"), Mapping):
            rows = []
            for split, block in payload["splits"].items():
                for row in block.get("records", []):
                    rows.append({"split": split, **row})
        else:
            rows = list(payload.get("records", [])) if isinstance(payload, Mapping) else []
    sources: dict[tuple[str, int], SeedSource] = {}
    for row in rows:
        date = str(row.get("date") or row.get("source_date") or "")[:10]
        seed = row.get("seed")
        episode_id = row.get("episode_id")
        split = _normalise_split(str(row.get("split") or ""))
        if not date or seed is None or episode_id is None or not split:
            continue
        source = SeedSource(
            date=date,
            seed=int(seed),
            episode_id=str(episode_id),
            split=split,
            source_relpath=str(row.get("source_relpath") or row.get("source_path") or ""),
        )
        sources.setdefault((date, int(seed)), source)
    if not sources:
        raise ValueError(f"no usable seed rows in {path}")
    return sorted(sources.values(), key=lambda item: (item.split, item.date, item.seed))


def stratified_panel(
    sources: Sequence[SeedSource],
    split: str,
    count: int,
    dates: Sequence[str],
    random_seed: int,
) -> list[SeedSource]:
    """Select a deterministic date-stratified panel without replacement."""

    split = _normalise_split(split)
    if count <= 0:
        raise ValueError("panel count must be positive")
    dates = tuple(str(item) for item in dates)
    quota = {date: count // len(dates) for date in dates}
    for date in dates[: count % len(dates)]:
        quota[date] += 1
    selected: list[SeedSource] = []
    for date in dates:
        values = [item for item in sources if item.split == split and item.date == date]
        rng = random.Random(int(random_seed) + _stable_int(f"{split}|{date}"))
        rng.shuffle(values)
        if len(values) < quota[date]:
            raise ValueError(
                f"not enough seeds for split={split} date={date}: "
                f"need {quota[date]}, have {len(values)}"
            )
        selected.extend(values[: quota[date]])
    random.Random(int(random_seed) + _stable_int(split)).shuffle(selected)
    return selected


def _root_lineage(spec: Mapping[str, Any], model_id: str) -> str:
    value = spec.get("root_lineage")
    if value:
        return str(value)
    lineage = spec.get("lineage")
    if isinstance(lineage, (list, tuple)) and lineage:
        return str(lineage[0])
    return str(lineage or model_id)


class CounterfactualSwitchAgent:
    """Run a candidate from one common anchor prefix and capture public state."""

    def __init__(self, anchor: Any, candidate: Any, same_agent: bool, switch_step: int = 72):
        self.anchor = anchor
        self.candidate = candidate
        self.same_agent = bool(same_agent)
        self.switch_step = int(switch_step)
        self._reset()

    def _reset(self) -> None:
        self.seen_prefix_steps: set[int] = set()
        self.prefix_match = True
        self.first_prefix_mismatch: int | None = None
        self.anchor_prefix = hashlib.sha256()
        self.candidate_prefix = hashlib.sha256()
        self.switch_features: list[float] | None = None
        self.switch_feature_sha256: str | None = None
        self.last_step = -1

    def __call__(self, obs: Any, configuration: Any = None):
        step_value = obs.get("step", 0) if isinstance(obs, Mapping) else getattr(obs, "step", 0)
        step = int(step_value or 0)
        if step == 0 or step < self.last_step:
            self._reset()
        self.last_step = step
        if step == self.switch_step and self.switch_features is None:
            vector = public_features(obs)
            self.switch_features = vector.astype(float).tolist()
            self.switch_feature_sha256 = hashlib.sha256(
                vector.astype("<f4", copy=False).tobytes()
            ).hexdigest()

        if step < self.switch_step:
            anchor_action = _copy_action(self.anchor(obs, configuration))
            candidate_action = (
                anchor_action
                if self.same_agent
                else _copy_action(self.candidate(obs, configuration))
            )
            anchor_blob = _canonical_json(anchor_action).encode("utf-8")
            candidate_blob = _canonical_json(candidate_action).encode("utf-8")
            self.anchor_prefix.update(anchor_blob)
            self.candidate_prefix.update(candidate_blob)
            self.seen_prefix_steps.add(step)
            if anchor_blob != candidate_blob:
                self.prefix_match = False
                if self.first_prefix_mismatch is None:
                    self.first_prefix_mismatch = step
            return anchor_action

        if self.same_agent:
            return _copy_action(self.anchor(obs, configuration))
        return _copy_action(self.candidate(obs, configuration))

    def diagnostics(self) -> dict[str, Any]:
        return {
            "switch_step": self.switch_step,
            "prefix_complete": self.seen_prefix_steps == set(range(self.switch_step)),
            "prefix_match": self.prefix_match,
            "first_prefix_mismatch": self.first_prefix_mismatch,
            "anchor_prefix_sha256": self.anchor_prefix.hexdigest(),
            "candidate_prefix_sha256": self.candidate_prefix.hexdigest(),
            "switch_feature_schema": FEATURE_SCHEMA,
            "switch_feature_dim": FEATURE_DIM,
            "switch_feature_sha256": self.switch_feature_sha256,
            "switch_features": self.switch_features,
        }


def _context_id(
    collection_fingerprint: str,
    source: Mapping[str, Any],
    router_seat: int,
    opponent_root_lineage: str,
) -> str:
    text = _canonical_json(
        {
            "collection": collection_fingerprint,
            "date": source["date"],
            "split": source["split"],
            "seed": source["seed"],
            "episode_id": source["episode_id"],
            "router_seat": router_seat,
            "opponent_root_lineage": opponent_root_lineage,
        }
    )
    return "context-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def build_tasks(
    registry_path: Path,
    candidates: Sequence[str],
    opponents: Sequence[str],
    panels: Mapping[str, Sequence[SeedSource]],
    anchor: str,
    switch_step: int,
) -> tuple[list[dict[str, Any]], str]:
    registry = load_registry(registry_path)
    registry_hash = registry_fingerprint(registry)
    implementation_hash = implementation_fingerprint()
    for model_id in [*candidates, *opponents, anchor]:
        registry.require(model_id)
    config = {
        "schema": GRID_SCHEMA,
        "collection_implementation_sha256": implementation_hash,
        "registry_sha256": registry_hash,
        "candidates": list(candidates),
        "opponents": list(opponents),
        "anchor": anchor,
        "switch_step": int(switch_step),
        "collector_implementation_sha256": collector_implementation_fingerprint(),
        "panels": {
            split: [asdict(item) for item in values] for split, values in sorted(panels.items())
        },
    }
    collection_fingerprint = hashlib.sha256(
        _canonical_json(config).encode("utf-8")
    ).hexdigest()
    tasks: list[dict[str, Any]] = []
    for split, sources in sorted(panels.items()):
        for source in sources:
            source_record = asdict(source)
            for opponent in opponents:
                opponent_spec = registry.require(opponent)
                opponent_root = _root_lineage(opponent_spec, opponent)
                for router_seat in (0, 1):
                    context_id = _context_id(
                        collection_fingerprint, source_record, router_seat, opponent_root
                    )
                    for candidate in candidates:
                        task_key = f"{context_id}|candidate:{candidate}|opponent:{opponent}"
                        tasks.append(
                            {
                                "schema": GRID_SCHEMA,
                                "task_id": "grid-"
                                + hashlib.sha256(task_key.encode("utf-8")).hexdigest()[:24],
                                "context_id": context_id,
                                "collection_fingerprint": collection_fingerprint,
                                "collection_implementation_sha256": implementation_hash,
                                "registry": str(registry_path.resolve()),
                                "registry_sha256": registry_hash,
                                "source": source_record,
                                "candidate": candidate,
                                "candidate_root_lineage": _root_lineage(
                                    registry.require(candidate), candidate
                                ),
                                "anchor": anchor,
                                "opponent": opponent,
                                "opponent_root_lineage": opponent_root,
                                "router_seat": router_seat,
                                "switch_step": int(switch_step),
                            }
                        )
    return tasks, collection_fingerprint


def _one_game(task: Mapping[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    base = {key: task[key] for key in task if key != "registry"}
    try:
        from kaggle_environments import make

        registry = load_registry(task["registry"])
        candidate_id = str(task["candidate"])
        anchor_id = str(task["anchor"])
        if candidate_id == anchor_id:
            anchor = create_agent(registry, anchor_id)
            candidate = anchor
            same_agent = True
        else:
            anchor = create_agent(registry, anchor_id)
            candidate = create_agent(registry, candidate_id)
            same_agent = False
        opponent = create_agent(registry, str(task["opponent"]))
        switch_agent = CounterfactualSwitchAgent(
            anchor, candidate, same_agent=same_agent, switch_step=int(task["switch_step"])
        )
        source = task["source"]
        seed = int(source["seed"])
        router_seat = int(task["router_seat"])
        random.seed(seed * 104729 + router_seat * 1009)
        np.random.seed((seed + router_seat * 65537) % (2**32 - 1))
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        agents = (
            [switch_agent, opponent]
            if router_seat == 0
            else [opponent, switch_agent]
        )
        env.run(agents)
        statuses = [str(state.status) for state in env.state]
        rewards = [float(state.reward or 0.0) for state in env.state]
        own_reward = rewards[router_seat]
        opponent_reward = rewards[1 - router_seat]
        margin = own_reward - opponent_reward
        diagnostics = switch_agent.diagnostics()
        base.update(
            {
                "engine": "kaggle_environments.make(kaggriculture)",
                "closed_loop": True,
                "trace_agent": False,
                "statuses": statuses,
                "rewards": rewards,
                "done": statuses == ["DONE", "DONE"],
                "candidate_reward": own_reward,
                "opponent_reward": opponent_reward,
                "candidate_margin": margin,
                "candidate_score": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0,
                **diagnostics,
                "error": None,
            }
        )
    except Exception as exc:
        base.update(
            {
                "closed_loop": True,
                "trace_agent": False,
                "statuses": [],
                "rewards": [],
                "done": False,
                "candidate_reward": None,
                "opponent_reward": None,
                "candidate_margin": None,
                "candidate_score": None,
                "prefix_complete": False,
                "prefix_match": False,
                "switch_features": None,
                "switch_feature_sha256": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    base["elapsed_seconds"] = time.perf_counter() - started
    return base


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
    return rows


def run_tasks(
    tasks: Sequence[dict[str, Any]],
    output: Path,
    workers: int,
    resume: bool,
    retry_errors: bool = False,
) -> list[dict[str, Any]]:
    output.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_jsonl(output) if resume else []
    completed = {
        str(row.get("task_id"))
        for row in existing
        if not retry_errors or row.get("error") is None
    }
    pending = [task for task in tasks if str(task["task_id"]) not in completed]
    mode = "a" if resume and output.exists() else "w"
    started = time.perf_counter()
    with output.open(mode, encoding="utf-8", buffering=1) as handle:
        if workers <= 1:
            iterator = ((_one_game(task), index) for index, task in enumerate(pending, 1))
            for row, index in iterator:
                handle.write(_canonical_json(row) + "\n")
                existing.append(row)
                if index % max(1, len(pending) // 20) == 0 or index == len(pending):
                    print(
                        _canonical_json(
                            {
                                "phase": "router_grid",
                                "completed": index,
                                "pending": len(pending),
                                "games_per_second": index
                                / max(1e-9, time.perf_counter() - started),
                            }
                        ),
                        flush=True,
                    )
        else:
            with ProcessPoolExecutor(max_workers=int(workers)) as pool:
                futures = {pool.submit(_one_game, task): task["task_id"] for task in pending}
                for index, future in enumerate(as_completed(futures), 1):
                    row = future.result()
                    handle.write(_canonical_json(row) + "\n")
                    existing.append(row)
                    if index % max(1, len(pending) // 20) == 0 or index == len(pending):
                        print(
                            _canonical_json(
                                {
                                    "phase": "router_grid",
                                    "completed": index,
                                    "pending": len(pending),
                                    "games_per_second": index
                                    / max(1e-9, time.perf_counter() - started),
                                }
                            ),
                            flush=True,
                        )
    # A retried error may coexist with its successful replacement.  Last row wins.
    deduplicated = {str(row.get("task_id")): row for row in existing}
    return list(deduplicated.values())


def summarise_grid(
    rows: Sequence[Mapping[str, Any]],
    tasks: Sequence[Mapping[str, Any]],
    candidates: Sequence[str],
    collection_fingerprint: str,
) -> dict[str, Any]:
    relevant = [
        dict(row)
        for row in rows
        if row.get("schema") == GRID_SCHEMA
        and row.get("collection_fingerprint") == collection_fingerprint
    ]
    by_context: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in relevant:
        by_context[str(row.get("context_id"))].append(row)
    context_audit: Counter[str] = Counter()
    for context_rows in by_context.values():
        valid = [
            row
            for row in context_rows
            if row.get("error") is None and row.get("done")
        ]
        observed_candidates = {str(row.get("candidate")) for row in valid}
        hashes = {row.get("switch_feature_sha256") for row in valid}
        if observed_candidates == set(candidates):
            context_audit["complete_candidate_grid"] += 1
        else:
            context_audit["incomplete_candidate_grid"] += 1
        if len(hashes) == 1 and None not in hashes:
            context_audit["feature_matched"] += 1
        else:
            context_audit["feature_mismatched"] += 1
        if valid and all(row.get("prefix_complete") and row.get("prefix_match") for row in valid):
            context_audit["all_prefix_compatible"] += 1
        else:
            context_audit["prefix_incompatible"] += 1
    stats: dict[str, Any] = {}
    for opponent in sorted({str(row.get("opponent_root_lineage")) for row in relevant}):
        stats[opponent] = {}
        for candidate in candidates:
            selected = [
                row
                for row in relevant
                if row.get("opponent_root_lineage") == opponent
                and row.get("candidate") == candidate
                and row.get("error") is None
                and row.get("done")
            ]
            stats[opponent][candidate] = {
                "games": len(selected),
                "score": float(np.mean([row["candidate_score"] for row in selected]))
                if selected
                else None,
                "mean_margin": float(np.mean([row["candidate_margin"] for row in selected]))
                if selected
                else None,
            }
    task_ids = {str(task["task_id"]) for task in tasks}
    observed_ids = {str(row.get("task_id")) for row in relevant}
    return {
        "schema": GRID_SUMMARY_SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "collection_fingerprint": collection_fingerprint,
        "feature_schema": FEATURE_SCHEMA,
        "feature_names": list(FEATURE_NAMES),
        "closed_loop": True,
        "trace_agent_used": False,
        "scheduled_games": len(tasks),
        "observed_games": len(task_ids & observed_ids),
        "missing_games": len(task_ids - observed_ids),
        "valid_done_games": sum(
            row.get("error") is None and row.get("done") for row in relevant
        ),
        "errors": sum(row.get("error") is not None for row in relevant),
        "not_done": sum(not row.get("done", False) for row in relevant),
        "contexts": len(by_context),
        "context_audit": dict(context_audit),
        "by_opponent_root_and_candidate": stats,
        "complete": task_ids <= observed_ids
        and all(row.get("error") is None and row.get("done") for row in relevant),
    }


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _model_list(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        result.extend(item.strip() for item in str(value).split(",") if item.strip())
    return list(dict.fromkeys(result))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--seed-manifest", type=Path, default=DEFAULT_SEED_MANIFEST)
    parser.add_argument("--splits", nargs="+", default=["train", "validation"])
    parser.add_argument("--dates", nargs="+", default=list(DEFAULT_DATES))
    parser.add_argument("--seeds-per-split", type=int, required=True)
    parser.add_argument("--candidates", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--opponents", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--anchor", default="baseline_v1")
    parser.add_argument("--switch-step", type=int, default=72)
    parser.add_argument("--random-seed", type=int, default=20260822)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, default=HERE / "router_outcome_grid.jsonl")
    parser.add_argument("--summary", type=Path, default=HERE / "router_outcome_grid_summary.json")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--max-tasks", type=int)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    candidates = _model_list(args.candidates)
    opponents = _model_list(args.opponents)
    requested_splits = {_normalise_split(item) for item in args.splits}
    if "test" in requested_splits:
        raise ValueError(
            "router grid collection refuses the sealed official test split; "
            "test opens only for the final frozen policy matrix"
        )
    if not requested_splits <= {"train", "validation"}:
        raise ValueError(f"unsupported training split(s): {sorted(requested_splits)}")
    if not candidates or not opponents:
        raise ValueError("at least one candidate and opponent are required")
    if args.max_tasks is not None and not args.smoke:
        raise ValueError("--max-tasks is restricted to --smoke runs")
    sources = load_seed_sources(args.seed_manifest)
    panels = {
        _normalise_split(split): stratified_panel(
            sources,
            _normalise_split(split),
            args.seeds_per_split,
            args.dates,
            args.random_seed,
        )
        for split in args.splits
    }
    tasks, fingerprint = build_tasks(
        args.registry.resolve(),
        candidates,
        opponents,
        panels,
        args.anchor,
        args.switch_step,
    )
    if args.max_tasks is not None:
        tasks = tasks[: args.max_tasks]
    rows = run_tasks(tasks, args.output, args.workers, args.resume, args.retry_errors)
    report = summarise_grid(rows, tasks, candidates, fingerprint)
    report["provenance"] = {
        "registry": str(args.registry.resolve()),
        "registry_sha256": registry_fingerprint(load_registry(args.registry)),
        "collection_implementation_sha256": implementation_fingerprint(),
        "seed_manifest": str(args.seed_manifest.resolve()),
        "splits": list(panels),
        "dates": list(args.dates),
        "seeds_per_split": args.seeds_per_split,
        "anchor": args.anchor,
        "switch_step": args.switch_step,
        "random_seed": args.random_seed,
        "candidates": candidates,
        "opponents": opponents,
        "smoke": bool(args.smoke),
    }
    _atomic_json(args.summary, report)
    print(
        _canonical_json(
            {
                "output": str(args.output.resolve()),
                "summary": str(args.summary.resolve()),
                "scheduled_games": report["scheduled_games"],
                "valid_done_games": report["valid_done_games"],
                "complete": report["complete"],
            }
        )
    )
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
