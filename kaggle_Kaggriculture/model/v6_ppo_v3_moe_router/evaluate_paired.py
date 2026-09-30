"""Independent, paired qualification evaluation for PPO v3 MoVE weights.

The evaluator never copies a candidate weight into the source checkout.  Each
worker creates a disposable submission-shaped directory, imports ``main.py``
from there, and evaluates that exact artifact.  This matters because ``main``
resolves ``router_weights.npz`` relative to its own file.

It is deliberately an *offline gate*, not a training rollout collector.  A
single report contains the direct V1 test, a family-stratified opponent pool,
paired bootstrap intervals, action-closure audit, DONE/DONE safety result and
both pure-router and end-to-end latency.  ``--stage`` records whether the
specified weight is the D2 Router checkpoint or an on-policy PPO checkpoint;
the NPZ serving schema intentionally remains identical for both stages.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import time
from typing import Any, Callable, Iterable

import numpy as np


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
V1_SOURCE = MODEL_ROOT / "v1_adaptive_market" / "main.py"
SERVING_FILES = ("main.py", "catalog.py", "experts.py", "action_compiler.py", "features.py", "router_numpy.py")
_IMPORT_NAMES = set(SERVING_FILES)
_IMPORT_NAMES.update(name[:-3] for name in SERVING_FILES)
_CANDIDATE_CACHE: dict[str, tuple[tempfile.TemporaryDirectory, Any]] = {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _seed_bucket(seed: int) -> int:
    digest = hashlib.sha256(str(int(seed)).encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big") % 100


def _partition_seeds(start: int, count: int, low: int = 90, high: int = 100) -> list[int]:
    """Select a stable holdout seed partition rather than a contiguous range."""
    result: list[int] = []
    candidate = int(start)
    while len(result) < int(count):
        if low <= _seed_bucket(candidate) < high:
            result.append(candidate)
        candidate += 7919
    return result


def _load_module(path: Path, name: str, *, isolated_names: Iterable[str] = ()):
    """Load a module with directory-local imports without leaking them globally.

    V4/V5 and the staged candidate have ordinary absolute imports such as
    ``import base_agent`` / ``from catalog import Catalog``.  Removing these
    short names after import is safe: their functions retain direct references
    to their already-imported module objects.  It also prevents a candidate
    package from accidentally using a source-tree ``catalog.py``.
    """
    names = {str(value) for value in isolated_names}
    saved = {key: sys.modules.pop(key) for key in names if key in sys.modules}
    old_path = list(sys.path)
    module_name = "%s_%s_%s" % (name, os.getpid(), time.time_ns())
    try:
        sys.path.insert(0, str(path.parent))
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError("unable to import %s" % path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = old_path
        # The returned function/module retains its globals by reference; the
        # transient import key is no longer needed.  Leaving one unique name
        # per game in ``sys.modules`` would leak memory in a 2,000-game gate.
        sys.modules.pop(module_name, None)
        for key in names:
            sys.modules.pop(key, None)
        sys.modules.update(saved)


def _stage_candidate(weights: Path):
    """Return a module that resolves ``weights`` in a disposable directory."""
    weights = Path(weights).resolve()
    key = str(weights)
    cached = _CANDIDATE_CACHE.get(key)
    if cached is not None:
        return cached[1]
    if not weights.is_file():
        raise FileNotFoundError(weights)
    temporary = tempfile.TemporaryDirectory(prefix="ppo_v3_eval_")
    root = Path(temporary.name) / "candidate"
    root.mkdir()
    for filename in SERVING_FILES:
        shutil.copy2(HERE / filename, root / filename)
    shutil.copy2(V1_SOURCE, root / "v1_agent.py")
    shutil.copy2(weights, root / "router_weights.npz")
    module = _load_module(root / "main.py", "ppo_v3_eval_candidate", isolated_names=_IMPORT_NAMES)
    # Force the loading failure to be visible in the report.  The submitted
    # agent deliberately falls back to V1 for invalid weights, but a training
    # gate must not accidentally certify that fallback as a neural candidate.
    module._load_router()
    _CANDIDATE_CACHE[key] = (temporary, module)
    return module


def _copy_action(action: Any) -> dict[str, Any]:
    action = action or {}
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(value or ["PASS"]) for value in (action.get("hands") or [])],
        "market": [list(value or []) for value in (action.get("market") or [])],
    }


def _module_opponent(path: Path, name: str) -> Callable:
    # Modules in these directories have different dependency names.  Isolate a
    # generous set so a prior candidate/import cannot change their behavior.
    module = _load_module(
        path,
        "ppo_v3_eval_%s" % name,
        isolated_names={"base_agent", "routes", "v1_fallback", "main", "catalog", "experts", "action_compiler", "features", "router_numpy"},
    )
    return module.agent


def _forced_v1(route: str) -> Callable:
    module = _load_module(V1_SOURCE, "ppo_v3_eval_%s" % route)
    target = module._HIGH_ROUTE_ACTIONS if route == "forced_high" else module._LOW_ROUTE_ACTIONS

    def agent(obs):
        module._ACTIONS = target
        return module._CORE_AGENT(obs)

    return agent


def _v1_mutation(kind: str) -> Callable:
    module = _load_module(V1_SOURCE, "ppo_v3_eval_%s" % kind)

    def agent(obs):
        action = _copy_action(module.agent(obs))
        step = int((obs or {}).get("step", 0) or 0)
        if kind.startswith("market_"):
            if kind == "market_delay":
                if step < 360:
                    action["market"] = [order for order in action["market"] if not order or order[0] != "SELL"]
            elif kind == "market_buy":
                if step < 480:
                    action["market"] = [order for order in action["market"] if not order or order[0] != "SELL"]
            elif kind == "market_priority":
                sells = [order for order in action["market"] if len(order) >= 2 and order[0] == "SELL"]
                other = [order for order in action["market"] if len(order) < 2 or order[0] != "SELL"]
                sells.sort(key=lambda order: (str(order[1]) not in {"MELON", "WOOL", "MILK", "STRAWBERRY"}, str(order[1])))
                action["market"] = sells + other
            else:
                scale = {"market_half": 0.5, "market_double": 2.0}.get(kind)
                if scale is None:
                    raise ValueError(kind)
                for order in action["market"]:
                    if len(order) >= 3 and order[0] == "SELL":
                        order[2] = max(0, int(round(int(order[2] or 0) * scale)))
        elif kind == "exploit_wheat":
            action["market"] = [order for order in action["market"] if not (len(order) >= 2 and order[0] == "BUY_PRODUCT" and order[1] == "WHEAT")]
        elif kind == "exploit_cleanup":
            # This family only changes the final two in-game days.  Earlier
            # calls are intentionally a no-op, not an unsupported mutation.
            if step >= 672:
                action["market"] = [order for order in action["market"] if len(order) >= 1 and order[0] == "SELL"]
        else:
            raise ValueError(kind)
        return action

    return agent


OPPONENT_FAMILIES = {
    "v0": "historical_rule", "v1": "v1_anchor", "v2": "survival_rule", "v3": "bc_ppo_legacy",
    "v4": "champion_rule", "v5": "champion_rule", "starter": "starter", "random": "random",
    "forced_low": "production_low", "forced_high": "production_high",
    "market_half": "market_quantity", "market_double": "market_quantity", "market_delay": "market_timing",
    "market_priority": "market_priority", "market_buy": "market_timing",
    "exploit_wheat": "exploiter", "exploit_cleanup": "exploiter",
}
DEFAULT_POOL = ("v0", "v1", "v2", "v3", "v4", "v5", "starter", "random", "forced_low", "forced_high", "market_half", "market_double", "market_delay", "market_priority", "market_buy", "exploit_wheat", "exploit_cleanup")


def _opponent(name: str) -> Callable:
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg

    name = str(name)
    files = {
        "v0": MODEL_ROOT / "v0_api_smoke" / "main.py",
        "v1": V1_SOURCE,
        "v2": MODEL_ROOT / "v2_survival_guard" / "main.py",
        "v3": MODEL_ROOT / "v3_bc_ppo_hybrid" / "main.py",
        "v4": MODEL_ROOT / "v4_rule_hybrid" / "main.py",
        "v5": MODEL_ROOT / "v5_rule_hybrid" / "main.py",
    }
    if name in files:
        return _module_opponent(files[name], name)
    if name == "starter":
        return kg.starter_agent
    if name == "random":
        return kg.random_agent
    if name in {"forced_low", "forced_high"}:
        return _forced_v1(name)
    if name in {"market_half", "market_double", "market_delay", "market_priority", "market_buy", "exploit_wheat", "exploit_cleanup"}:
        return _v1_mutation(name)
    raise ValueError("unsupported opponent: %s" % name)


def _audit_summary(candidate: Any, seat: int) -> dict[str, Any]:
    game = getattr(candidate, "_GAMES", {}).get(int(seat))
    audits = list((game or {}).get("audit", []) or [])
    result = {
        "agent_calls": len(audits),
        "effective_action_changes": 0,
        "compiler_fallbacks": 0,
        "terminal_guard_calls": 0,
        "opening_frozen_calls": 0,
        "production_choices": {},
        "market_choices": {},
    }
    for row in audits:
        if bool(row.get("effective_action_change", False)):
            result["effective_action_changes"] += 1
        if bool(row.get("fallback_used", False)):
            result["compiler_fallbacks"] += 1
        if bool(row.get("terminal_guard_applied", False)):
            result["terminal_guard_calls"] += 1
        if bool(row.get("frozen_opening", False)):
            result["opening_frozen_calls"] += 1
        production = str(row.get("production_expert") or "unknown")
        market = str(row.get("market_expert") or "M_NONE")
        result["production_choices"][production] = result["production_choices"].get(production, 0) + 1
        result["market_choices"][market] = result["market_choices"].get(market, 0) + 1
    return result


def _one_game(task: dict[str, Any]) -> dict[str, Any]:
    """Worker-local game.  All exceptions become explicit gate evidence."""
    try:
        from kaggle_environments import make

        seed, seat = int(task["seed"]), int(task["seat"])
        # Some Kaggle helper opponents use Python's global RNG.  Make their
        # behavior reproducible under worker scheduling without touching the
        # environment's separate seed contract.
        random.seed(seed * 7 + seat * 17 + int(task["index"]))
        np.random.seed((seed + seat * 101 + int(task["index"])) % (2**32 - 1))
        if task["candidate_kind"] == "v1_anchor":
            candidate = _opponent("v1")
            candidate_module = None
        else:
            candidate_module = _stage_candidate(Path(task["weights"]))
            candidate = candidate_module.agent
        opponent = _opponent(str(task["opponent"]))
        agents = [candidate, opponent] if seat == 0 else [opponent, candidate]
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.reset(2)
        call_ms: list[float] = []
        hour0_ms: list[float] = []
        for step in range(719):
            for state in env.state:
                state.observation.step = step
            obs = env.state[seat].observation
            started = time.perf_counter_ns()
            own = candidate(obs)
            elapsed = (time.perf_counter_ns() - started) / 1_000_000.0
            call_ms.append(elapsed)
            if step % 24 == 0:
                hour0_ms.append(elapsed)
            other = opponent(env.state[1 - seat].observation)
            env.step([own, other] if seat == 0 else [other, own])
        statuses = [str(state.status) for state in env.state]
        rewards = [float(state.reward or 0.0) for state in env.state]
        margin = rewards[seat] - rewards[1 - seat]
        row = {
            "index": int(task["index"]), "seed": seed, "seat": seat,
            "candidate_kind": str(task["candidate_kind"]), "opponent": str(task["opponent"]),
            "family": OPPONENT_FAMILIES.get(str(task["opponent"]), "unknown"),
            "candidate_gold": rewards[seat], "opponent_gold": rewards[1 - seat], "margin": margin,
            "score": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0,
            "status": statuses, "done": statuses == ["DONE", "DONE"], "error": None,
            "agent_call_mean_ms": float(np.mean(call_ms)), "agent_call_p95_ms": float(np.quantile(call_ms, 0.95)),
            "daily_call_mean_ms": float(np.mean(hour0_ms)), "daily_call_p95_ms": float(np.quantile(hour0_ms, 0.95)),
        }
        if candidate_module is not None:
            row["model_status"] = candidate_module.model_status()
            row["audit"] = _audit_summary(candidate_module, seat)
        return row
    except Exception as exc:
        return {
            "index": int(task["index"]), "seed": int(task["seed"]), "seat": int(task["seat"]),
            "candidate_kind": str(task["candidate_kind"]), "opponent": str(task["opponent"]),
            "family": OPPONENT_FAMILIES.get(str(task["opponent"]), "unknown"),
            "candidate_gold": None, "opponent_gold": None, "margin": None, "score": None,
            "status": [], "done": False, "error": "%s: %s" % (type(exc).__name__, exc),
        }


def _run(tasks: list[dict[str, Any]], workers: int) -> list[dict[str, Any]]:
    if not tasks:
        return []
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=max(1, int(workers))) as pool:
        futures = [pool.submit(_one_game, task) for task in tasks]
        every = max(1, len(tasks) // 10)
        for completed, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if completed % every == 0 or completed == len(tasks):
                print(json.dumps({"phase": "evaluate", "completed": completed, "games": len(tasks), "games_per_second": completed / max(1e-9, time.perf_counter() - started)}), flush=True)
    return sorted(rows, key=lambda row: int(row["index"]))


def _bootstrap(values: Iterable[float], rounds: int, seed: int) -> list[float | None]:
    values = np.asarray(list(values), dtype=np.float64)
    if len(values) == 0 or not np.all(np.isfinite(values)):
        return [None, None]
    rng = np.random.default_rng(int(seed))
    samples = np.empty(int(rounds), dtype=np.float64)
    for start in range(0, int(rounds), 500):
        count = min(500, int(rounds) - start)
        indices = rng.integers(0, len(values), size=(count, len(values)))
        samples[start:start + count] = values[indices].mean(axis=1)
    return [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]


def _finite(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("error") is None and row.get("done") and row.get("score") is not None]


def _seed_means(rows: Iterable[dict[str, Any]], field: str) -> list[float]:
    """Return only complete two-seat seed clusters for a paired interval."""
    grouped: dict[int, dict[int, float]] = {}
    for row in _finite(rows):
        value = row.get(field)
        if value is not None and np.isfinite(float(value)):
            grouped.setdefault(int(row["seed"]), {})[int(row["seat"])] = float(value)
    return [float(np.mean([grouped[seed][0], grouped[seed][1]])) for seed in sorted(grouped) if set(grouped[seed]) == {0, 1}]


def _paired_score_by_seed(rows: Iterable[dict[str, Any]]) -> dict[int, float]:
    grouped: dict[int, dict[int, float]] = {}
    for row in _finite(rows):
        grouped.setdefault(int(row["seed"]), {})[int(row["seat"])] = float(row["score"])
    return {
        seed: float(np.mean([by_seat[0], by_seat[1]]))
        for seed, by_seat in grouped.items()
        if set(by_seat) == {0, 1}
    }


def _summarise_candidate(rows: list[dict[str, Any]], bootstrap_rounds: int, seed: int) -> dict[str, Any]:
    valid = _finite(rows)
    scores = _seed_means(valid, "score")
    margins = _seed_means(valid, "margin")
    audits = [row["audit"] for row in valid if "audit" in row]
    calls = [row.get("agent_call_mean_ms") for row in valid if row.get("agent_call_mean_ms") is not None]
    daily = [row.get("daily_call_mean_ms") for row in valid if row.get("daily_call_mean_ms") is not None]
    summary: dict[str, Any] = {
        "games": len(rows), "valid_games": len(valid), "seed_pairs": len(scores),
        "score_rate": float(np.mean(scores)) if scores else None,
        "score_bootstrap_ci95": _bootstrap(scores, bootstrap_rounds, seed),
        "mean_gold_margin": float(np.mean(margins)) if margins else None,
        "margin_bootstrap_ci95": _bootstrap(margins, bootstrap_rounds, seed + 1),
        "safety": {
            "done_done_games": sum(bool(row.get("done")) for row in rows),
            "failed_games": sum(not bool(row.get("done")) for row in rows),
            "errors": [row.get("error") for row in rows if row.get("error")][:10],
        },
        "agent_latency_ms": {
            "mean_of_game_means": float(np.mean(calls)) if calls else None,
            "p95_of_game_means": float(np.quantile(calls, 0.95)) if calls else None,
            "daily_mean_of_game_means": float(np.mean(daily)) if daily else None,
        },
    }
    if audits:
        production: dict[str, int] = {}
        market: dict[str, int] = {}
        for audit in audits:
            for key, value in audit["production_choices"].items():
                production[key] = production.get(key, 0) + int(value)
            for key, value in audit["market_choices"].items():
                market[key] = market.get(key, 0) + int(value)
        calls_count = max(1, sum(int(audit["agent_calls"]) for audit in audits))
        summary["action_closure"] = {
            "agent_calls": calls_count,
            "effective_action_changes": sum(int(audit["effective_action_changes"]) for audit in audits),
            "effective_action_change_rate": sum(int(audit["effective_action_changes"]) for audit in audits) / calls_count,
            "compiler_fallbacks": sum(int(audit["compiler_fallbacks"]) for audit in audits),
            "terminal_guard_calls": sum(int(audit["terminal_guard_calls"]) for audit in audits),
            "opening_frozen_calls": sum(int(audit["opening_frozen_calls"]) for audit in audits),
            "production_choices": production, "market_choices": market,
        }
    return summary


def _stage(weights: Path, explicit: str) -> str:
    if explicit != "auto":
        return explicit
    parent = Path(weights).resolve().parent
    if (parent / "ppo_router_report.json").is_file():
        return "ppo"
    if (parent / "router_training_report.json").is_file():
        return "router"
    return "unknown"


def _router_latency(weights: Path, repeats: int = 10000) -> dict[str, Any]:
    candidate = _stage_candidate(Path(weights))
    router = candidate._load_router()
    status = candidate.model_status()
    if router is None:
        return {"loaded": False, "error": status.get("error"), "mean_ms": None, "p95_ms": None, "repeats": 0}
    # Single-model encoding weights are [F,H], while an ensemble stores
    # [K,F,H].  The feature axis is therefore always the penultimate one.
    feature_dim = int(router.arrays["enc_w"].shape[-2])
    feature = np.zeros(feature_dim, dtype=np.float32)
    for _ in range(100):
        router.predict(feature)
    elapsed: list[float] = []
    for _ in range(int(repeats)):
        started = time.perf_counter_ns()
        router.predict(feature)
        elapsed.append((time.perf_counter_ns() - started) / 1_000_000.0)
    return {"loaded": True, "error": None, "mean_ms": float(np.mean(elapsed)), "p95_ms": float(np.quantile(elapsed, 0.95)), "max_ms": float(np.max(elapsed)), "repeats": int(repeats)}


def evaluate(
    weights: Path,
    *,
    paired_seeds: int = 1000,
    pool_seeds: int = 100,
    opponents: Iterable[str] = DEFAULT_POOL,
    workers: int = 12,
    bootstrap_rounds: int = 10000,
    stage: str = "auto",
    output: Path | None = None,
) -> dict[str, Any]:
    """Evaluate a Router or PPO checkpoint without mutating the source tree."""
    weights = Path(weights).resolve()
    stage = _stage(weights, stage)
    opponents = tuple(str(value) for value in opponents)
    unknown = [name for name in opponents if name not in OPPONENT_FAMILIES]
    if unknown:
        raise ValueError("unknown opponents: %s" % unknown)
    # Read-only preflight and direct Numpy latency.  Candidate games run in
    # child processes, so this also catches a schema/model mismatch early.
    direct_latency = _router_latency(weights)
    direct_seeds = _partition_seeds(98100000, paired_seeds)
    tasks: list[dict[str, Any]] = []
    index = 0
    for seed in direct_seeds:
        for seat in (0, 1):
            tasks.append({"index": index, "seed": seed, "seat": seat, "candidate_kind": "candidate", "opponent": "v1", "weights": str(weights)})
            index += 1
    direct_rows = _run(tasks, workers)

    pool_tasks: list[dict[str, Any]] = []
    for opponent_index, opponent in enumerate(opponents):
        seeds = _partition_seeds(71100000 + opponent_index * 1_000_003, pool_seeds)
        for candidate_kind in ("v1_anchor", "candidate"):
            for seed in seeds:
                for seat in (0, 1):
                    pool_tasks.append({"index": index, "seed": seed, "seat": seat, "candidate_kind": candidate_kind, "opponent": opponent, "weights": str(weights)})
                    index += 1
    pool_rows = _run(pool_tasks, workers)
    direct = _summarise_candidate(direct_rows, bootstrap_rounds, 193)
    pool: dict[str, Any] = {}
    for opponent in opponents:
        candidate_rows = [row for row in pool_rows if row["opponent"] == opponent and row["candidate_kind"] == "candidate"]
        anchor_rows = [row for row in pool_rows if row["opponent"] == opponent and row["candidate_kind"] == "v1_anchor"]
        candidate = _summarise_candidate(candidate_rows, bootstrap_rounds, 11 + len(pool))
        anchor = _summarise_candidate(anchor_rows, bootstrap_rounds, 97 + len(pool))
        # First average both seats, then take candidate-anchor by seed.  An
        # interrupted one-seat result is never allowed into the CI as an
        # independent observation.
        candidate_mean = _paired_score_by_seed(candidate_rows)
        anchor_mean = _paired_score_by_seed(anchor_rows)
        delta = [candidate_mean[seed] - anchor_mean[seed] for seed in sorted(set(candidate_mean).intersection(anchor_mean))]
        pool[opponent] = {
            "family": OPPONENT_FAMILIES[opponent], "candidate": candidate, "v1_anchor": anchor,
            "score_delta_vs_v1": float(np.mean(delta)) if delta else None,
            "score_delta_bootstrap_ci95": _bootstrap(delta, bootstrap_rounds, 501 + len(pool)),
            "paired_seed_count": len(delta),
        }
    model_statuses = [row.get("model_status") for row in _finite(direct_rows) if row.get("model_status")]
    all_pool_deltas = [value["score_delta_vs_v1"] for value in pool.values() if value["score_delta_vs_v1"] is not None]
    result: dict[str, Any] = {
        "schema": "kaggriculture-ppo-v3-move-evaluation-2",
        "weights": str(weights), "weights_sha256": _sha256(weights), "stage": stage,
        "serving_contract": {"temporary_candidate_package": True, "source_tree_weight_mutation": False, "model_status": model_statuses[0] if model_statuses else None},
        "router_latency_ms": direct_latency,
        "direct_vs_v1": direct,
        "pool": pool,
        "pool_mean_score_delta_vs_v1": float(np.mean(all_pool_deltas)) if all_pool_deltas else None,
        "rows": {"direct": direct_rows, "pool": pool_rows},
    }
    direct_lower = direct["score_bootstrap_ci95"][0]
    result["gates"] = {
        "weights_loaded": bool(direct_latency["loaded"]) and all(bool(status.get("loaded")) for status in model_statuses),
        "all_games_done_done": direct["safety"]["failed_games"] == 0 and all(value["candidate"]["safety"]["failed_games"] == 0 and value["v1_anchor"]["safety"]["failed_games"] == 0 for value in pool.values()),
        "direct_score_rate_ge_53pct": direct["score_rate"] is not None and direct["score_rate"] >= 0.53,
        "direct_bootstrap_lower_gt_50pct": direct_lower is not None and direct_lower > 0.50,
        "pool_mean_better_than_v1": result["pool_mean_score_delta_vs_v1"] is not None and result["pool_mean_score_delta_vs_v1"] > 0.0,
        "no_family_decline_gt_2pp": all(value["score_delta_vs_v1"] is not None and value["score_delta_vs_v1"] >= -0.02 for value in pool.values()),
        "router_predict_p95_lt_5ms": direct_latency["p95_ms"] is not None and direct_latency["p95_ms"] < 5.0,
    }
    if output is not None:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True, help="D2 Router or D3 PPO exported router_weights.npz")
    parser.add_argument("--stage", choices=("auto", "router", "ppo"), default="auto", help="training stage for report attribution")
    parser.add_argument("--paired-seeds", type=int, default=1000, help="holdout seeds in the direct, double-seat V1 gate")
    parser.add_argument("--pool-seeds", type=int, default=100, help="holdout seeds per opponent family, always double-seat")
    parser.add_argument("--opponents", nargs="+", default=list(DEFAULT_POOL))
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--bootstrap-rounds", type=int, default=10000)
    parser.add_argument("--output", type=Path, default=HERE / "evaluation_report.json")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.weights, paired_seeds=args.paired_seeds, pool_seeds=args.pool_seeds, opponents=args.opponents, workers=args.workers, bootstrap_rounds=args.bootstrap_rounds, stage=args.stage, output=args.output), ensure_ascii=False, indent=2))
