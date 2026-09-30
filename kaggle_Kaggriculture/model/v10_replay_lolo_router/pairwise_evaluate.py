"""Closed-loop, resumable pairwise evaluation on official 2026-08-18..20 seeds.

Historical episode files are used only to recover a date-stratified panel of
official environment seeds.  Every task creates a fresh Kaggle environment and
two live agents; no historical action is replayed and no ``TraceAgent`` exists
in this evaluator.

Formal default: 100 source seeds x both seat assignments = 200 games for every
unordered model pair.  The same seed panel is used for all pairs, enabling
paired comparisons and later contextual-router evaluation.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import random
import sys
import time
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

try:
    from .agent_factory import Registry, create_agent, load_registry, registry_fingerprint
    from .router import RuleSelector, ShadowRouter, public_features
except ImportError:  # direct-script compatibility
    from agent_factory import Registry, create_agent, load_registry, registry_fingerprint
    from router import RuleSelector, ShadowRouter, public_features


HERE = Path(__file__).resolve().parent
DEFAULT_DATES = ("2026-08-18", "2026-08-19", "2026-08-20")
SCHEMA = "kaggriculture-v10-pairwise-closed-loop-1"
FINAL_PANEL_SCHEMA = "kaggriculture-v10-frozen-test-panel-1"


def implementation_fingerprint() -> str:
    """Hash the evaluator path separately from submitted-agent code.

    Registry fingerprints deliberately cover serving dependencies only.  A
    resume is valid only when this evaluator, its loading layer, public feature
    encoder, Python ABI and Kaggle engine version are also unchanged.
    """

    import kaggle_environments

    digest = hashlib.sha256()
    runtime = {
        "python": list(sys.version_info[:2]),
        "kaggle_environments": getattr(kaggle_environments, "__version__", "unknown"),
        "numpy": np.__version__,
    }
    digest.update(json.dumps(runtime, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    for path in (
        Path(__file__).resolve(),
        HERE / "agent_factory.py",
        HERE / "router.py",
        HERE / "freeze_test_panel.py",
    ):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


@dataclass(frozen=True)
class SeedRecord:
    date: str
    seed: int
    episode_id: str
    split: str
    source_path: str = ""
    lineage_fold: str = ""


def _stable_bucket(text: str, modulo: int = 100) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % int(modulo)


def _derived_split(date: str, seed: int) -> str:
    bucket = _stable_bucket(f"kaggriculture-v10-seed-split:{date}:{int(seed)}")
    return "train" if bucket < 60 else "validation" if bucket < 80 else "test"


def _normalise_seed_row(
    row: Mapping[str, Any], inherited_date: str = "", inherited_split: str = ""
) -> SeedRecord | None:
    date = str(row.get("date") or row.get("source_date") or row.get("day") or inherited_date or "")[:10]
    seed = row.get("seed", row.get("environment_seed", row.get("env_seed")))
    info = row.get("info") if isinstance(row.get("info"), Mapping) else {}
    if seed is None:
        seed = info.get("seed")
    if seed is None or not date:
        return None
    episode = row.get("episode_id", row.get("episodeId", row.get("id", info.get("EpisodeId", ""))))
    split = str(row.get("split") or row.get("seed_split") or inherited_split or _derived_split(date, int(seed))).lower()
    if split == "val":
        split = "validation"
    return SeedRecord(
        date=date,
        seed=int(seed),
        episode_id=str(episode or f"{date}-{int(seed)}"),
        split=split,
        source_path=str(row.get("source_path") or row.get("source_relpath") or row.get("path") or row.get("file") or ""),
        lineage_fold=str(row.get("lineage_fold") or row.get("fold") or ""),
    )


def _rows_from_json(
    payload: Any, inherited_date: str = "", inherited_split: str = ""
) -> Iterable[SeedRecord]:
    if isinstance(payload, list):
        for row in payload:
            yield from _rows_from_json(row, inherited_date, inherited_split)
        return
    if not isinstance(payload, Mapping):
        return
    direct = _normalise_seed_row(payload, inherited_date, inherited_split)
    if direct is not None:
        yield direct
        return
    # Accept both a standard records array and date -> records mappings.  This
    # makes the evaluator independent of the manifest builder's presentation.
    for key in ("records", "episodes", "seeds", "rows", "items", "evaluation_seeds"):
        if key in payload:
            yield from _rows_from_json(payload[key], inherited_date, inherited_split)
    splits = payload.get("splits")
    if isinstance(splits, Mapping):
        for split_name, split_payload in splits.items():
            normalised = "validation" if str(split_name).lower() == "val" else str(split_name).lower()
            yield from _rows_from_json(split_payload, inherited_date, normalised)
    for key, value in payload.items():
        if len(str(key)) >= 10 and str(key)[:10] in DEFAULT_DATES and isinstance(value, (list, Mapping)):
            yield from _rows_from_json(value, str(key)[:10], inherited_split)


def load_seed_manifest(path: str | Path) -> list[SeedRecord]:
    path = Path(path).expanduser().resolve()
    suffix = path.suffix.lower()
    rows: list[SeedRecord] = []
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                record = _normalise_seed_row(row)
                if record is not None:
                    rows.append(record)
    elif suffix in {".jsonl", ".ndjson"}:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.extend(_rows_from_json(json.loads(line)))
    else:
        rows.extend(_rows_from_json(json.loads(path.read_text(encoding="utf-8"))))
    unique: dict[tuple[str, int], SeedRecord] = {}
    for row in rows:
        unique.setdefault((row.date, row.seed), row)
    if not unique:
        raise ValueError(f"no seed records in {path}")
    return sorted(unique.values(), key=lambda item: (item.date, item.seed, item.episode_id))


def stratified_seed_panel(
    records: Sequence[SeedRecord],
    count: int,
    dates: Sequence[str],
    split: str,
    random_seed: int,
) -> list[SeedRecord]:
    dates = tuple(str(item) for item in dates)
    wanted_split = str(split).lower()
    by_date: dict[str, list[SeedRecord]] = {}
    for date in dates:
        values = [item for item in records if item.date == date and (wanted_split == "all" or item.split == wanted_split)]
        if not values:
            raise ValueError(f"manifest has no {wanted_split!r} seeds for {date}")
        rng = random.Random(int(random_seed) + _stable_bucket(date, 1_000_003))
        rng.shuffle(values)
        by_date[date] = values
    quota = {date: count // len(dates) for date in dates}
    for date in dates[: count % len(dates)]:
        quota[date] += 1
    panel: list[SeedRecord] = []
    used_seeds: set[int] = set()
    missing: dict[str, int] = {}
    for date in dates:
        if quota[date] == 0:
            continue
        selected = []
        for item in by_date[date]:
            # A seed repeated on two source dates is still the same stochastic
            # environment and must not masquerade as an independent sample.
            if item.seed in used_seeds:
                continue
            selected.append(item)
            used_seeds.add(item.seed)
            if len(selected) == quota[date]:
                break
        panel.extend(selected)
        if len(selected) < quota[date]:
            missing[date] = quota[date] - len(selected)
    if missing:
        raise ValueError(f"not enough globally unique seeds for stratified panel: {missing}")
    # Final deterministic shuffle removes date blocks without changing quotas.
    random.Random(int(random_seed)).shuffle(panel)
    return panel


class ObservedAgent:
    """Capture the public step-72 feature vector and underlying diagnostics."""

    def __init__(self, handle: Any, switch_step: int = 72):
        self.handle = handle
        self.switch_step = int(switch_step)
        self.switch_features: list[float] | None = None
        self.switch_feature_hash: str | None = None
        self.calls = 0

    def __call__(self, obs: Any, configuration: Any = None):
        step = int(getattr(obs, "step", None) if getattr(obs, "step", None) is not None else (obs.get("step", 0) if isinstance(obs, Mapping) else 0))
        if step == 0:
            self.switch_features = None
            self.switch_feature_hash = None
            self.calls = 0
        self.calls += 1
        if step == self.switch_step and self.switch_features is None:
            vector = public_features(obs)
            self.switch_features = vector.astype(float).tolist()
            self.switch_feature_hash = hashlib.sha256(vector.astype("<f4", copy=False).tobytes()).hexdigest()
        return self.handle(obs, configuration)

    def diagnostics(self) -> dict[str, Any]:
        method = getattr(self.handle, "diagnostics", None)
        underlying = dict(method()) if callable(method) else {}
        return {
            "calls": self.calls,
            "switch_features": self.switch_features,
            "switch_feature_hash": self.switch_feature_hash,
            "router": underlying if underlying.get("kind") == "shadow_full_expert_router" else None,
            "underlying": underlying if underlying and underlying.get("kind") != "shadow_full_expert_router" else None,
        }


def evaluation_fingerprint(
    registry: Registry,
    model_ids: Sequence[str],
    panel: Sequence[SeedRecord],
    games_per_pair: int,
    include_self_play: bool = False,
) -> str:
    payload = {
        "schema": SCHEMA,
        "evaluation_implementation_sha256": implementation_fingerprint(),
        "registry_and_code_sha256": registry_fingerprint(registry),
        "models": list(model_ids),
        "games_per_pair": int(games_per_pair),
        "include_self_play": bool(include_self_play),
        "seed_panel": [asdict(item) for item in panel],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _task_id(run_fingerprint: str, pair_id: str, source: SeedRecord, a_seat: int) -> str:
    text = f"{run_fingerprint}:{pair_id}:{source.date}:{source.episode_id}:{source.seed}:a-seat-{a_seat}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def build_tasks(
    registry: Registry,
    model_ids: Sequence[str],
    panel: Sequence[SeedRecord],
    run_fingerprint: str,
    include_self_play: bool = False,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    pairs = list(itertools.combinations(model_ids, 2))
    if include_self_play:
        pairs.extend((item, item) for item in model_ids)
    for model_a, model_b in pairs:
        pair_id = f"{model_a}__vs__{model_b}"
        for source in panel:
            for a_seat in (0, 1):
                tasks.append({
                    "task_id": _task_id(run_fingerprint, pair_id, source, a_seat),
                    "run_fingerprint": run_fingerprint,
                    "pair_id": pair_id,
                    "model_a": model_a,
                    "model_b": model_b,
                    "model_a_seat": a_seat,
                    "source": asdict(source),
                    "registry": str(registry.path),
                })
    return tasks


def _one_game(task: Mapping[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    base = {
        "schema": SCHEMA,
        "task_id": str(task["task_id"]),
        "run_fingerprint": str(task["run_fingerprint"]),
        "pair_id": str(task["pair_id"]),
        "model_a": str(task["model_a"]),
        "model_b": str(task["model_b"]),
        "model_a_seat": int(task["model_a_seat"]),
        "source": dict(task["source"]),
    }
    try:
        from kaggle_environments import make

        registry = load_registry(task["registry"])
        spec_a, spec_b = registry.require(base["model_a"]), registry.require(base["model_b"])
        raw_a = create_agent(registry, base["model_a"])
        raw_b = create_agent(registry, base["model_b"])
        agent_a, agent_b = ObservedAgent(raw_a), ObservedAgent(raw_b)
        a_seat = base["model_a_seat"]
        agents = [agent_a, agent_b] if a_seat == 0 else [agent_b, agent_a]
        source = base["source"]
        seed = int(source["seed"])
        random.seed(seed * 104729 + a_seat * 1009)
        np.random.seed((seed + a_seat * 65537) % (2**32 - 1))
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.run(agents)
        statuses = [str(state.status) for state in env.state]
        rewards = [float(state.reward or 0.0) for state in env.state]
        reward_a, reward_b = rewards[a_seat], rewards[1 - a_seat]
        margin = reward_a - reward_b
        base.update({
            "engine": "kaggle_environments.make(kaggriculture)",
            "closed_loop": True,
            "trace_agent": False,
            "seat_models": [base["model_a"], base["model_b"]] if a_seat == 0 else [base["model_b"], base["model_a"]],
            "statuses": statuses,
            "rewards": rewards,
            "done": statuses == ["DONE", "DONE"],
            "reward_a": reward_a,
            "reward_b": reward_b,
            "margin_a": margin,
            "score_a": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0,
            "model_meta": {
                base["model_a"]: {"family": spec_a.get("family"), "lineage": spec_a.get("lineage"), "tags": spec_a.get("tags", [])},
                base["model_b"]: {"family": spec_b.get("family"), "lineage": spec_b.get("lineage"), "tags": spec_b.get("tags", [])},
            },
            "agent_diagnostics": {
                base["model_a"]: agent_a.diagnostics(),
                base["model_b"]: agent_b.diagnostics(),
            },
            # Unlike the model-keyed convenience mapping, this remains
            # unambiguous for self-play where both IDs are identical.
            "seat_diagnostics": [agent_a.diagnostics(), agent_b.diagnostics()] if a_seat == 0 else [agent_b.diagnostics(), agent_a.diagnostics()],
            "error": None,
        })
    except Exception as exc:
        base.update({
            "closed_loop": True,
            "trace_agent": False,
            "seat_models": [], "statuses": [], "rewards": [], "done": False,
            "reward_a": None, "reward_b": None, "margin_a": None, "score_a": None,
            "model_meta": {}, "agent_diagnostics": {}, "seat_diagnostics": [],
            "error": f"{type(exc).__name__}: {exc}",
        })
    base["elapsed_seconds"] = time.perf_counter() - started
    return base


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
    return rows


def run_tasks(tasks: Sequence[dict[str, Any]], jsonl: Path, workers: int, resume: bool) -> list[dict[str, Any]]:
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_jsonl(jsonl) if resume else []
    # Failed or non-DONE rows remain resumable.  A later successful record with
    # the same task id supersedes the failure during summary deduplication.
    completed = {
        str(row.get("task_id")) for row in existing
        if row.get("error") is None and row.get("done") is True
    }
    pending = [task for task in tasks if str(task["task_id"]) not in completed]
    mode = "a" if resume and jsonl.exists() else "w"
    started = time.perf_counter()
    with jsonl.open(mode, encoding="utf-8", buffering=1) as output:
        if workers <= 1:
            iterator = enumerate((_one_game(task) for task in pending), 1)
            for index, row in iterator:
                output.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                existing.append(row)
                if index % max(1, len(pending) // 20) == 0 or index == len(pending):
                    print(json.dumps({"phase": "evaluate", "completed": index, "pending": len(pending), "games_per_second": index / max(1e-9, time.perf_counter() - started)}), flush=True)
        else:
            with ProcessPoolExecutor(max_workers=int(workers)) as pool:
                futures = {pool.submit(_one_game, task): task["task_id"] for task in pending}
                for index, future in enumerate(as_completed(futures), 1):
                    row = future.result()
                    output.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                    existing.append(row)
                    if index % max(1, len(pending) // 20) == 0 or index == len(pending):
                        print(json.dumps({"phase": "evaluate", "completed": index, "pending": len(pending), "games_per_second": index / max(1e-9, time.perf_counter() - started)}), flush=True)
    return existing


def _paired_seed_scores(rows: Sequence[Mapping[str, Any]]) -> list[float]:
    grouped: dict[tuple[str, str, int], dict[int, float]] = defaultdict(dict)
    for row in rows:
        if row.get("error") is None and row.get("done") and row.get("score_a") is not None:
            source = row["source"]
            key = (str(source["date"]), str(source["episode_id"]), int(source["seed"]))
            grouped[key][int(row["model_a_seat"])] = float(row["score_a"])
    return [float(np.mean([seats[0], seats[1]])) for seats in grouped.values() if set(seats) == {0, 1}]


def _bootstrap_mean(values: Sequence[float], seed: int, rounds: int = 4000) -> list[float | None]:
    array = np.asarray(values, dtype=np.float64)
    if not len(array):
        return [None, None]
    rng = np.random.default_rng(int(seed))
    samples = np.empty(int(rounds), dtype=np.float64)
    for start in range(0, rounds, 500):
        count = min(500, rounds - start)
        indices = rng.integers(0, len(array), size=(count, len(array)))
        samples[start:start + count] = array[indices].mean(axis=1)
    return [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]


def summarise(
    rows: Sequence[dict[str, Any]],
    model_ids: Sequence[str],
    games_per_pair: int,
    expected_task_ids: set[str],
    run_fingerprint: str,
    include_self_play: bool = False,
) -> dict[str, Any]:
    deduplicated: dict[str, dict[str, Any]] = {}
    for row in rows:
        task_id = str(row.get("task_id") or "")
        if task_id not in expected_task_ids or row.get("run_fingerprint") != run_fingerprint:
            continue
        previous = deduplicated.get(task_id)
        success = row.get("error") is None and row.get("done") is True
        previous_success = previous is not None and previous.get("error") is None and previous.get("done") is True
        if previous is None or success or not previous_success:
            deduplicated[task_id] = row
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in deduplicated.values():
        if row.get("schema") == SCHEMA:
            by_pair[str(row["pair_id"])].append(row)
    pair_summary: dict[str, Any] = {}
    matrix = {model: {other: (0.5 if model == other else None) for other in model_ids} for model in model_ids}
    failures: list[dict[str, Any]] = []
    for pair_id, pair_rows in sorted(by_pair.items()):
        a, b = pair_id.split("__vs__", 1)
        valid = [row for row in pair_rows if row.get("error") is None and row.get("done") and row.get("score_a") is not None]
        scores = [float(row["score_a"]) for row in valid]
        margins = [float(row["margin_a"]) for row in valid]
        paired = _paired_seed_scores(valid)
        date_stats = {}
        for date in DEFAULT_DATES:
            date_values = [float(row["score_a"]) for row in valid if row["source"]["date"] == date]
            if date_values:
                date_stats[date] = {"games": len(date_values), "score_rate_a": float(np.mean(date_values))}
        summary = {
            "model_a": a, "model_b": b,
            "scheduled_games": games_per_pair,
            "observed_games": len(pair_rows), "valid_games": len(valid), "paired_seeds": len(paired),
            "complete": len(pair_rows) == games_per_pair and len(valid) == games_per_pair and len(paired) == games_per_pair // 2,
            "wins_a": sum(value == 1.0 for value in scores),
            "ties": sum(value == 0.5 for value in scores),
            "losses_a": sum(value == 0.0 for value in scores),
            "score_rate_a": float(np.mean(scores)) if scores else None,
            "paired_score_rate_a": float(np.mean(paired)) if paired else None,
            "paired_score_ci95": _bootstrap_mean(paired, _stable_bucket(pair_id, 2**31 - 1)),
            "mean_margin_a": float(np.mean(margins)) if margins else None,
            "by_date": date_stats,
            "errors": sum(row.get("error") is not None for row in pair_rows),
            "not_done": sum(not row.get("done", False) for row in pair_rows),
        }
        pair_summary[pair_id] = summary
        if summary["paired_score_rate_a"] is not None and a != b:
            matrix[a][b] = summary["paired_score_rate_a"]
            matrix[b][a] = 1.0 - summary["paired_score_rate_a"]
        elif summary["paired_score_rate_a"] is not None:
            matrix[a][a] = summary["paired_score_rate_a"]
        if not summary["complete"]:
            failures.append({"pair_id": pair_id, "valid_games": len(valid), "paired_seeds": len(paired)})
    expected_pairs = len(model_ids) * (len(model_ids) - 1) // 2 + (len(model_ids) if include_self_play else 0)
    return {
        "schema": "kaggriculture-v10-pairwise-summary-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_fingerprint": run_fingerprint,
        "closed_loop": True,
        "trace_agent_used": False,
        "models": list(model_ids),
        "expected_pairs": expected_pairs,
        "observed_pairs": len(pair_summary),
        "games_per_pair": int(games_per_pair),
        "include_self_play": bool(include_self_play),
        "formal_gate_complete": len(pair_summary) == expected_pairs and not failures,
        "expected_tasks": len(expected_task_ids),
        "deduplicated_tasks": len(deduplicated),
        "incomplete_pairs": failures,
        "pairs": pair_summary,
        "score_matrix": matrix,
    }


def _one_prefix_check(registry_path: str, expert_ids: Sequence[str], anchor: str, opponent_id: str, source: SeedRecord, router_seat: int, switch_step: int) -> dict[str, Any]:
    try:
        from kaggle_environments import make

        registry = load_registry(registry_path)
        experts = {item: create_agent(registry, item) for item in expert_ids}
        specs = {item: registry.require(item) for item in expert_ids}
        pseudo_spec = {"id": "prefix_validator", "rule": {"default_priority": [anchor]}}
        router = ShadowRouter("prefix_validator", experts, specs, anchor, RuleSelector(pseudo_spec, specs, anchor), switch_step)
        opponent = create_agent(registry, opponent_id)
        env = make("kaggriculture", configuration={"seed": int(source.seed)}, debug=False)
        env.reset(2)
        for step in range(int(switch_step) + 1):
            for state in env.state:
                state.observation.step = step
            own = router(env.state[router_seat].observation)
            other = opponent(env.state[1 - router_seat].observation)
            env.step([own, other] if router_seat == 0 else [other, own])
        return {
            "date": source.date, "seed": source.seed, "episode_id": source.episode_id,
            "router_seat": router_seat, "error": None, "diagnostics": router.diagnostics(),
        }
    except Exception as exc:
        return {
            "date": source.date, "seed": source.seed, "episode_id": source.episode_id,
            "router_seat": router_seat, "error": f"{type(exc).__name__}: {exc}", "diagnostics": {},
        }


def prefix_check(registry: Registry, expert_ids: Sequence[str], anchor: str, opponent: str, panel: Sequence[SeedRecord], switch_step: int) -> dict[str, Any]:
    rows = [
        _one_prefix_check(str(registry.path), expert_ids, anchor, opponent, source, seat, switch_step)
        for source in panel for seat in (0, 1)
    ]
    compatible = {}
    for model_id in expert_ids:
        compatible[model_id] = all(
            row.get("error") is None
            and row["diagnostics"].get("prefix_complete")
            and row["diagnostics"].get("prefix_match", {}).get(model_id) is True
            for row in rows
        )
    return {
        "schema": "kaggriculture-v10-step72-prefix-validation-1",
        "switch_step": int(switch_step), "experts": list(expert_ids), "anchor": anchor,
        "opponent": opponent, "closed_loop": True, "trace_agent_used": False,
        "all_compatible": all(compatible.values()), "compatible": compatible, "rows": rows,
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_terminal_test_registry(
    registry: Registry, model_ids: Sequence[str]
) -> dict[str, Any]:
    """Preflight the goal-achieved V11 pool before a 16-model test run."""

    from kaggle_Kaggriculture.model.v11_iterative_league.league import (
        TARGET_BASELINES,
        load_state,
        model_fingerprints,
    )

    raw = registry.raw
    if raw.get("schema") != "kaggriculture-v11-terminal-pool-registry-1":
        raise ValueError("16-model final test requires a terminal V11 registry schema")
    if raw.get("sealed_before_final_test") is not True:
        raise ValueError("16-model terminal registry is not sealed before final test")
    if raw.get("test_used_for_fit") is not False or raw.get(
        "pre_selection_test_access"
    ) is not False:
        raise ValueError("16-model terminal registry does not prove a clean test freeze")
    if raw.get("evaluation_implementation_sha256") != implementation_fingerprint():
        raise ValueError("terminal registry was sealed for a different evaluator/runtime")
    terminal = raw.get("league_terminal_state") or {}
    state_path = Path(str(terminal.get("path") or "")).expanduser().resolve()
    if not state_path.is_file() or _file_sha256(state_path) != terminal.get(
        "file_sha256"
    ):
        raise ValueError("terminal league-state file/hash mismatch")
    state = load_state(state_path)
    models = [str(item) for item in model_ids]
    baselines = set(str(item) for item in TARGET_BASELINES)
    goal = state.get("goal") or {}
    if (
        state.get("status") != "goal_achieved"
        or goal.get("achieved") is not True
        or goal.get("achieved_after_round") is None
        or len(models) != 16
        or [str(item) for item in (state.get("active_models") or [])] != models
        or set(models) & baselines
        or set(goal.get("required_absent_models") or []) != baselines
        or int(goal.get("required_pool_size") or -1) != 16
        or state.get("pending_candidate")
        or state.get("candidate_required")
    ):
        raise ValueError("terminal league goal/model pool is not exact")
    if (
        terminal.get("state_sha256") != state.get("state_sha256")
        or terminal.get("active_models") != models
        or terminal.get("achieved_after_round") != goal.get("achieved_after_round")
    ):
        raise ValueError("terminal registry seal differs from league state")
    source_path = Path(str(terminal.get("source_pool_registry") or "")).expanduser()
    if not source_path.is_absolute():
        source_path = (state_path.parent / source_path).resolve()
    source = load_registry(source_path)
    if (
        _file_sha256(source.path)
        != terminal.get("source_pool_registry_file_sha256")
        or registry_fingerprint(source)
        != terminal.get("source_pool_registry_and_code_sha256")
        or registry_fingerprint(source) != state.get("registry_and_code_sha256")
    ):
        raise ValueError("terminal source pool registry/file fingerprint mismatch")
    current_fingerprints = model_fingerprints(registry, models)
    source_fingerprints = model_fingerprints(source, models)
    state_fingerprints = {
        model_id: str(
            (state.get("model_entries") or {})
            .get(model_id, {})
            .get("serving_sha256")
            or ""
        )
        for model_id in models
    }
    if (
        current_fingerprints != source_fingerprints
        or current_fingerprints != state_fingerprints
        or current_fingerprints != terminal.get("serving_fingerprints")
    ):
        raise ValueError("terminal 16-model serving fingerprints changed")
    return {
        "schema": raw.get("schema"),
        "sealed_before_final_test": True,
        "league_state": str(state_path),
        "league_state_file_sha256": terminal.get("file_sha256"),
        "league_state_sha256": state.get("state_sha256"),
        "goal_achieved_after_round": goal.get("achieved_after_round"),
        "source_pool_registry_file_sha256": terminal.get(
            "source_pool_registry_file_sha256"
        ),
        "source_pool_registry_and_code_sha256": terminal.get(
            "source_pool_registry_and_code_sha256"
        ),
        "serving_fingerprints_sha256": hashlib.sha256(
            json.dumps(
                current_fingerprints,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "original_baselines_absent": True,
    }


def load_sealed_test_panel(
    registry: Registry,
    model_ids: Sequence[str],
    panel_path: Path,
    manifest_path: Path,
    quarantine_path: Path,
) -> tuple[list[SeedRecord], dict[str, Any]]:
    """Load the pre-test-frozen panel; never sample the canonical test pool."""

    # For the dynamic 16-model terminal pool, prove the league goal and all
    # serving fingerprints *before* opening any test-manifest/panel/quarantine
    # metadata.  A placeholder or pre-goal registry must have zero test access.
    terminal_provenance = (
        validate_terminal_test_registry(registry, model_ids)
        if len(model_ids) == 16
        else None
    )

    try:
        from .freeze_test_panel import validate_payload
    except ImportError:  # direct-script compatibility
        from freeze_test_panel import validate_payload

    panel_path = panel_path.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    quarantine_path = quarantine_path.expanduser().resolve()
    payload = json.loads(panel_path.read_text(encoding="utf-8"))
    records = list(validate_payload(payload, manifest_path, quarantine_path))
    protocol = registry.raw.get("test_protocol") or {}
    if registry.raw.get("sealed_before_test") is not True:
        raise ValueError("final test registry is not marked sealed before test")
    expected = {
        "source_manifest_sha256": _file_sha256(manifest_path),
        "quarantine_file_sha256": _file_sha256(quarantine_path),
        "clean_pool_records_sha256": payload.get("clean_pool_records_sha256"),
        "frozen_panel_file_sha256": _file_sha256(panel_path),
        "frozen_panel_records_sha256": payload.get("records_sha256"),
        "panel_sources": 100,
        "games_per_pair": 200,
        "unordered_pairs": len(model_ids) * (len(model_ids) - 1) // 2,
        "expected_games": len(model_ids) * (len(model_ids) - 1) // 2 * 200,
        "salt": 20260822,
        "model_ids": list(model_ids),
    }
    mismatched = {
        key: {"registry": protocol.get(key), "current": value}
        for key, value in expected.items()
        if protocol.get(key) != value
    }
    if mismatched:
        raise ValueError(f"final test protocol differs from sealed registry: {mismatched}")
    if list(model_ids) != list(registry.models):
        raise ValueError("final test model order must equal the sealed 14-model registry")
    if len(model_ids) not in {14, 16}:
        raise ValueError("sealed final test requires exactly 14 or 16 frozen models")
    return records, {
        "frozen_panel": str(panel_path),
        "frozen_panel_file_sha256": expected["frozen_panel_file_sha256"],
        "frozen_panel_records_sha256": expected["frozen_panel_records_sha256"],
        "source_manifest_sha256": expected["source_manifest_sha256"],
        "quarantine": str(quarantine_path),
        "quarantine_file_sha256": expected["quarantine_file_sha256"],
        "clean_pool_records_sha256": expected["clean_pool_records_sha256"],
        "clean_test_sources": int(payload.get("clean_test_sources") or 0),
        "quarantined_sources": int(payload.get("quarantined_sources") or 0),
        "date_quota": dict((payload.get("selection") or {}).get("date_quota") or {}),
        "salt": int((payload.get("selection") or {}).get("salt") or 0),
        "terminal_pool": terminal_provenance,
    }


def _model_list(values: Sequence[str]) -> list[str]:
    result = []
    for value in values:
        result.extend(item.strip() for item in str(value).split(",") if item.strip())
    return list(dict.fromkeys(result))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--seed-manifest", type=Path, required=True)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--dates", nargs="+", default=list(DEFAULT_DATES))
    parser.add_argument("--split", choices=("train", "validation", "test", "all"), default="test")
    parser.add_argument("--games-per-pair", type=int, default=200)
    parser.add_argument("--random-seed", type=int, default=20260822)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, default=HERE / "pairwise_summary.json")
    parser.add_argument("--jsonl", type=Path, default=HERE / "pairwise_games.jsonl")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--smoke", action="store_true", help="allow fewer than 200 games per pair")
    parser.add_argument("--include-self-play", action="store_true", help="add per-model self-play needed for a complete Router outcome grid")
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--merge-jsonl", type=Path, nargs="*", default=[], help="additional shard JSONLs for summary-only merge")
    parser.add_argument("--prefix-check", action="store_true")
    parser.add_argument("--prefix-opponent")
    parser.add_argument("--switch-step", type=int, default=72)
    parser.add_argument("--frozen-panel", type=Path, default=HERE / "final_test_panel.json")
    parser.add_argument("--quarantine", type=Path, default=HERE / "test_exposure_quarantine.json")
    args = parser.parse_args()

    registry = load_registry(args.registry)
    model_ids = _model_list(args.models)
    for model_id in model_ids:
        registry.require(model_id)
    if len(model_ids) < 2:
        raise ValueError("at least two models are required")
    if args.games_per_pair % 2:
        raise ValueError("games-per-pair must be even for balanced seats")
    if args.games_per_pair < 200 and not args.smoke:
        raise ValueError("formal evaluation requires at least 200 games per pair; use --smoke only for development")
    if not (0 <= args.shard_index < args.num_shards):
        raise ValueError("invalid shard index")
    test_protocol_provenance: dict[str, Any] | None = None
    if args.split == "test":
        if args.smoke:
            raise ValueError("development smoke runs are forbidden on the sealed test split")
        if args.prefix_check:
            raise ValueError("prefix checks must use train/validation, never sealed test")
        if args.include_self_play:
            raise ValueError("sealed final test is exactly 91 distinct unordered pairs")
        if args.games_per_pair != 200:
            raise ValueError("sealed final test requires exactly 200 games per pair")
        if args.random_seed != 20260822 or tuple(args.dates) != DEFAULT_DATES:
            raise ValueError("sealed final test salt/dates cannot be changed")
        if not args.resume and not args.summary_only:
            raise ValueError("sealed final test must use resumable append-only execution")
        panel, test_protocol_provenance = load_sealed_test_panel(
            registry,
            model_ids,
            args.frozen_panel,
            args.seed_manifest,
            args.quarantine,
        )
    else:
        records = load_seed_manifest(args.seed_manifest)
        panel = stratified_seed_panel(
            records,
            args.games_per_pair // 2,
            args.dates,
            args.split,
            args.random_seed,
        )
    if args.prefix_check:
        opponent = args.prefix_opponent or model_ids[0]
        report = prefix_check(registry, model_ids, model_ids[0], opponent, panel, args.switch_step)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(args.output), "all_compatible": report["all_compatible"]}, ensure_ascii=False))
        return

    run_fingerprint = evaluation_fingerprint(registry, model_ids, panel, args.games_per_pair, args.include_self_play)
    all_tasks = build_tasks(registry, model_ids, panel, run_fingerprint, args.include_self_play)
    tasks = [task for task in all_tasks if _stable_bucket(task["task_id"], args.num_shards) == args.shard_index]
    if args.summary_only:
        rows = []
        for path in [args.jsonl, *args.merge_jsonl]:
            rows.extend(_read_jsonl(path))
    else:
        rows = run_tasks(tasks, args.jsonl, args.workers, args.resume)
    report = summarise(
        rows, model_ids, args.games_per_pair, {task["task_id"] for task in all_tasks},
        run_fingerprint, args.include_self_play,
    )
    report["provenance"] = {
        "registry": str(registry.path), "registry_sha256": registry_fingerprint(registry),
        "registry_file_sha256": _file_sha256(registry.path),
        "evaluation_implementation_sha256": implementation_fingerprint(),
        "seed_manifest": str(args.seed_manifest.resolve()), "dates": list(args.dates), "split": args.split,
        "random_seed": args.random_seed, "seed_panel": [asdict(item) for item in panel],
        "num_shards": args.num_shards, "shard_index": args.shard_index,
        "run_fingerprint": run_fingerprint,
        "jsonl": str(args.jsonl.resolve()),
        "merged_jsonl": [str(path.resolve()) for path in args.merge_jsonl],
        "sealed_test_protocol": test_protocol_provenance,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "formal_gate_complete": report["formal_gate_complete"], "observed_pairs": report["observed_pairs"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
