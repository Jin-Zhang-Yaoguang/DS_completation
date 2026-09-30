#!/usr/bin/env python3
"""Preregistered RC9 target/market predictor ablation on exposed R3 seeds.

The planner freezes a complete task denominator and all source hashes before
execution.  The runner never selects seeds, opponents, variants, or fixed
paths from outcomes.  This is a mechanism diagnostic, not gold evidence.
"""

from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import sys
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[2]
RC8 = MODEL / "v116_heuristic_gold_search/rc8_parametric_search"
SEARCH_PATH = RC8 / "search/search.py"
R3_RUN = RC8 / "search/runs/rc8_r1r2r3_global_001"
R3_SUMMARY = R3_RUN / "R3_summary.json"
R3_RUN_MANIFEST = R3_RUN / "run_manifest.json"
DIAGNOSE_PATH = HERE.parent / "diagnosis/diagnose.py"
FACTORY_PATH = MODEL / "v10_replay_lolo_router/agent_factory.py"
EXPECTED_R3_SEEDS = (1641819451, 915926955)
EXPECTED_GOLD = (
    "v19", "v20", "v21", "v32", "v33", "v34", "v37", "v46", "v51",
    "v52", "v53", "v54", "v66", "v70", "v71", "v72", "v73", "v76",
)
CORE_VARIANTS = ("base", "target_only", "market_only", "full")
FIXED_VARIANTS = ("fixed_collision", "fixed_scarcity", "fixed_liquidator")
SCHEMA = "v116-rc9-ablation-preregistered-v1"


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


SEARCH = load_module(SEARCH_PATH, "rc9_ablation_search_support")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
                      default=str, allow_nan=False).encode("utf-8")


def hash_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


def load_p0064() -> dict[str, Any]:
    summary = json.loads(R3_SUMMARY.read_text(encoding="utf-8"))
    rows = [row for row in summary.get("results", [])
            if str(row.get("config_id", "")).startswith("p0064_")]
    if len(rows) != 1 or summary["results"][0]["config_id"] != rows[0]["config_id"]:
        raise ValueError("R3 p0064 must be unique and first-ranked")
    return rows[0]


def load_exact_seeds() -> list[int]:
    manifest = json.loads(R3_RUN_MANIFEST.read_text(encoding="utf-8"))
    raw = manifest.get("seed_panels", {}).get("R3")
    if not isinstance(raw, list):
        raise ValueError("R3 run manifest has no R3 seed panel")
    seeds = [int(row["seed"] if isinstance(row, Mapping) else row) for row in raw]
    if tuple(seeds) != EXPECTED_R3_SEEDS:
        raise ValueError(f"R3 seed drift: expected {EXPECTED_R3_SEEDS}, got {tuple(seeds)}")
    return seeds


def variant_specs(include_fixed: bool) -> list[dict[str, Any]]:
    names = [*CORE_VARIANTS, *(FIXED_VARIANTS if include_fixed else ())]
    return [{
        "variant_id": name,
        "mode": name,
        "target_predictor": name in {"target_only", "full", *FIXED_VARIANTS},
        "market_predictor": name in {"market_only", "full", *FIXED_VARIANTS},
        "fixed_path": name.removeprefix("fixed_") if name.startswith("fixed_") else None,
        "diagnostic_only": True,
    } for name in names]


def variant_hash(spec: Mapping[str, Any]) -> str:
    return hash_value({"domain": "v116-rc9-ablation-variant-v1", "spec": dict(spec)})


def candidate_param_hash(candidate: Path, params: Mapping[str, Any], expected: str) -> str:
    module = load_module(candidate, f"rc9_candidate_preflight_{hash_value(str(candidate))[:12]}")
    builder = getattr(module, "build_executor", None)
    if not callable(builder):
        raise ValueError("candidate must expose build_executor(params, mode)")
    hasher = getattr(module, "canonical_hash", None)
    if not callable(hasher):
        raise ValueError("candidate must expose canonical_hash(params)")
    actual = str(hasher(dict(params)))
    if actual != expected:
        raise ValueError(f"candidate param hash drift: {actual} != {expected}")
    return actual


def validate_variant_contract(candidate: Path, params: Mapping[str, Any],
                              variants: Sequence[Mapping[str, Any]]) -> None:
    """Fail before preregistration unless every frozen mode is constructible."""
    for spec in variants:
        mode = str(spec["mode"])
        executor = SEARCH.load_candidate_executor(
            str(candidate), params, mode, f"rc9_contract_{mode}",
        )
        if not callable(getattr(executor, "diagnostics", None)):
            raise TypeError(f"mode={mode}: executor must expose callable diagnostics()")


def engine_artifact() -> Path:
    builds = sorted((SEARCH.CPPSIM / "build").glob("lib.*/kagsim*.so"))
    if not builds:
        raise FileNotFoundError("kagsim shared object missing")
    return builds[-1]


def source_hashes(candidate: Path, variants: Sequence[Mapping[str, Any]],
                  opponents: Mapping[str, Path]) -> dict[str, Any]:
    engine = engine_artifact()
    return {
        "candidate_path": str(candidate),
        "candidate_tree_sha256": SEARCH.sha256_python_tree(candidate.parent),
        "candidate_file_sha256": sha256_file(candidate),
        "evaluator_sha256": sha256_file(Path(__file__).resolve()),
        "search_support_sha256": sha256_file(SEARCH_PATH),
        "diagnosis_support_sha256": sha256_file(DIAGNOSE_PATH),
        "r3_summary_sha256": sha256_file(R3_SUMMARY),
        "r3_run_manifest_sha256": sha256_file(R3_RUN_MANIFEST),
        "agent_factory_sha256": sha256_file(FACTORY_PATH),
        "kagsim_path": str(engine),
        "kagsim_sha256": sha256_file(engine),
        "opponents": {name: {"path": str(path), "sha256": sha256_file(path)}
                      for name, path in opponents.items()},
        "variants": {str(spec["variant_id"]): variant_hash(spec) for spec in variants},
    }


def make_task_key(variant: str, opponent: str, seed: int, seat: int) -> str:
    return f"{variant}__{opponent}__{seed}__s{seat}"


def build_tasks(variants: Sequence[Mapping[str, Any]], opponents: Mapping[str, Path],
                seeds: Sequence[int], params: Mapping[str, Any], param_hash: str,
                candidate: Path, hashes: Mapping[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for variant in variants:
        identifier = str(variant["variant_id"])
        vhash = str(hashes["variants"][identifier])
        for opponent, path in opponents.items():
            ohash = str(hashes["opponents"][opponent]["sha256"])
            for seed in seeds:
                for seat in (0, 1):
                    identity = {
                        "variant_id": identifier, "variant_spec_hash": vhash,
                        "param_hash": param_hash,
                        "candidate_tree_sha256": hashes["candidate_tree_sha256"],
                        "evaluator_sha256": hashes["evaluator_sha256"],
                        "opponent_hash": ohash, "seed": int(seed), "seat": seat,
                        "mode": variant["mode"],
                    }
                    tasks.append({
                        "task_id": make_task_key(identifier, opponent, int(seed), seat),
                        "cache_key": hash_value(identity),
                        "variant_id": identifier,
                        "variant_spec": dict(variant),
                        "variant_spec_hash": vhash,
                        "param_hash": param_hash,
                        "params": dict(params),
                        "candidate_path": str(candidate),
                        "candidate_tree_sha256": hashes["candidate_tree_sha256"],
                        "evaluator_sha256": hashes["evaluator_sha256"],
                        "mode": variant["mode"],
                        "opponent": opponent,
                        "opponent_path": str(path),
                        "opponent_hash": ohash,
                        "seed": int(seed),
                        "candidate_seat": seat,
                    })
    return tasks


def plan(candidate: Path, include_fixed: bool, workers: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not 1 <= workers <= 8:
        raise ValueError("workers must be in [1,8]")
    candidate = candidate.expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    compile(candidate.read_text(encoding="utf-8"), str(candidate), "exec")
    SEARCH.validate_candidate_interface(candidate)
    config = load_p0064()
    variants = variant_specs(include_fixed)
    candidate_param_hash(candidate, config["params"], str(config["param_hash"]))
    validate_variant_contract(candidate, config["params"], variants)
    seeds = load_exact_seeds()
    opponents = dict(SEARCH.FULL_GOLD)
    if tuple(opponents) != EXPECTED_GOLD or len(opponents) != 18:
        raise ValueError("18-gold pool drift")
    if any(not path.is_file() for path in opponents.values()):
        raise FileNotFoundError("one or more gold opponents are missing")
    hashes = source_hashes(candidate, variants, opponents)
    tasks = build_tasks(variants, opponents, seeds, config["params"],
                        str(config["param_hash"]), candidate, hashes)
    expected = len(variants) * 18 * 2 * 2
    if len(tasks) != expected or len({task["task_id"] for task in tasks}) != expected:
        raise ValueError("task denominator mismatch or duplicate task IDs")
    task_plan_hash = hash_value([
        {key: task[key] for key in ("task_id", "cache_key", "variant_spec_hash",
                                    "opponent_hash", "seed", "candidate_seat", "mode")}
        for task in tasks
    ])
    manifest = {
        "schema": SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "mechanism_ablation_only_not_advancement",
        "config_id": config["config_id"],
        "param_hash": config["param_hash"],
        "params": config["params"],
        "variants": variants,
        "include_fixed_paths": include_fixed,
        "gold_opponents": list(opponents),
        "r3_exposed_seeds": seeds,
        "both_seats": True,
        "planned_games": expected,
        "planned_games_per_variant": 72,
        "planned_base_pairs": (len(variants) - 1) * 72,
        "planned_synergy_rows": 72,
        "workers": workers,
        "max_workers": 8,
        "source_hashes": hashes,
        "task_plan_sha256": task_plan_hash,
        "seed_list_sha256": hash_value(seeds),
        "uses_development": False,
        "uses_confirmation": False,
        "planned_denominator_frozen": True,
        "candidate_schema_required_zero": True,
        "calls_required_per_game": 719,
        "diagnostics_required": True,
        "gold_evidence": False,
    }
    manifest["run_fingerprint"] = hash_value({key: value for key, value in manifest.items()
                                               if key != "created_at_utc"})
    return manifest, tasks


def error_row(task: Mapping[str, Any], error: str) -> dict[str, Any]:
    return {
        "task_id": task["task_id"], "cache_key": task["cache_key"],
        "variant_id": task["variant_id"], "variant_spec_hash": task["variant_spec_hash"],
        "opponent": task["opponent"], "opponent_hash": task["opponent_hash"],
        "seed": int(task["seed"]), "candidate_seat": int(task["candidate_seat"]),
        "mode": task["mode"], "status": "ERROR", "error": error, "calls": 0,
        "candidate_schema_violations": 0, "candidate_schema_examples": [],
        "opponent_schema_violations": 0, "opponent_schema_examples": [],
        "first_shop": None, "diagnostics": None, "diagnostic_trace": [],
        "candidate_action_sha256": None, "opponent_action_sha256": None,
        "candidate_bank": None, "opponent_bank": None, "margin": None,
        "win": 0, "tie": 0, "loss": 0, "score": 0.0,
    }


def clean_diagnostics(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("executor.diagnostics() must return a mapping")
    return json.loads(json.dumps(dict(value), ensure_ascii=True, default=str, allow_nan=False))


def play_task(task: Mapping[str, Any]) -> dict[str, Any]:
    base = error_row(task, "uninitialised")
    calls = 0
    candidate_violations = 0
    opponent_violations = 0
    candidate_examples: list[str] = []
    opponent_examples: list[str] = []
    first_shop: str | None = None
    candidate_trace = hashlib.sha256()
    opponent_trace = hashlib.sha256()
    diagnostic_trace: list[dict[str, Any]] = []
    previous_diagnostic_hash: str | None = None
    final_diagnostics: dict[str, Any] = {}
    try:
        kagsim, Registry, create_agent = SEARCH.load_runtime()
        executor = SEARCH.load_candidate_executor(
            str(task["candidate_path"]), task["params"], str(task["mode"]), str(task["task_id"]),
        )
        diagnostics_method = getattr(executor, "diagnostics", None)
        if not callable(diagnostics_method):
            raise AttributeError("executor must expose diagnostics()")
        registry = Registry(path=HERE / "runtime_registry.json", models={}, raw={})
        opponent = create_agent(registry, {
            "id": f"rc9_ablation_{os.getpid()}_{hash_value(task['task_id'])[:12]}",
            "kind": "python", "path": str(task["opponent_path"]), "entrypoint": "agent",
        })
        game = kagsim.Game(int(task["seed"]))
        seat = int(task["candidate_seat"])
        while not game.done:
            observations = [game.observe(0), game.observe(1)]
            own_obs, rival_obs = observations[seat], observations[1 - seat]
            shops = list(((own_obs.get("town") or {}).get("unlocked_shops", [])) or [])
            if first_shop is None and shops:
                first_shop = str(shops[0])
            own_action = executor.act(own_obs)
            rival_action = opponent(rival_obs)
            own_issues = SEARCH.validate_action(own_action, own_obs)
            rival_issues = SEARCH.validate_action(rival_action, rival_obs)
            candidate_violations += len(own_issues)
            opponent_violations += len(rival_issues)
            if len(candidate_examples) < 20:
                candidate_examples.extend(f"step={calls}:{x}" for x in own_issues[:20-len(candidate_examples)])
            if len(opponent_examples) < 20:
                opponent_examples.extend(f"step={calls}:{x}" for x in rival_issues[:20-len(opponent_examples)])
            candidate_trace.update(canonical_bytes(own_action) + b"\n")
            opponent_trace.update(canonical_bytes(rival_action) + b"\n")
            final_diagnostics = clean_diagnostics(diagnostics_method())
            diagnostic_hash = hash_value(final_diagnostics)
            if diagnostic_hash != previous_diagnostic_hash:
                diagnostic_trace.append({"step": calls, "sha256": diagnostic_hash,
                                         "diagnostics": final_diagnostics})
                previous_diagnostic_hash = diagnostic_hash
            actions: list[Any] = [None, None]
            actions[seat], actions[1 - seat] = own_action, rival_action
            game.step(actions[0], actions[1])
            calls += 1
        rewards = [float(game.reward(0)), float(game.reward(1))]
        margin = rewards[seat] - rewards[1 - seat]
        return {
            **base, "status": "DONE", "error": None, "calls": calls,
            "candidate_schema_violations": candidate_violations,
            "candidate_schema_examples": candidate_examples,
            "opponent_schema_violations": opponent_violations,
            "opponent_schema_examples": opponent_examples,
            "first_shop": first_shop or "NO_SHOP", "diagnostics": final_diagnostics,
            "diagnostic_trace": diagnostic_trace,
            "candidate_action_sha256": candidate_trace.hexdigest(),
            "opponent_action_sha256": opponent_trace.hexdigest(),
            "candidate_bank": rewards[seat], "opponent_bank": rewards[1-seat],
            "margin": margin, "win": int(margin > 0), "tie": int(margin == 0),
            "loss": int(margin < 0), "score": int(margin > 0) + .5 * int(margin == 0),
        }
    except BaseException as exc:
        row = error_row(task, f"{type(exc).__name__}: {exc}")
        row.update({
            "calls": calls,
            "candidate_schema_violations": candidate_violations,
            "candidate_schema_examples": candidate_examples,
            "opponent_schema_violations": opponent_violations,
            "opponent_schema_examples": opponent_examples,
            "first_shop": first_shop,
            "diagnostics": final_diagnostics or None,
            "diagnostic_trace": diagnostic_trace,
            "candidate_action_sha256": candidate_trace.hexdigest(),
            "opponent_action_sha256": opponent_trace.hexdigest(),
        })
        return row


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    planned = len(rows)
    done = [row for row in rows if row.get("status") == "DONE"]
    return {
        "planned_games": planned,
        "completed_games": len(done),
        "errors_as_nonwins": planned - len(done),
        "wins": sum(int(row.get("win", 0)) for row in rows),
        "ties": sum(int(row.get("tie", 0)) for row in rows),
        "losses": sum(int(row.get("loss", 0)) for row in rows),
        "pure_win_rate_planned": (sum(int(row.get("win", 0)) for row in rows) / planned
                                  if planned else 0.0),
        "mean_candidate_bank_completed": (statistics.mean(float(row["candidate_bank"])
                                                            for row in done) if done else None),
        "mean_margin_completed": (statistics.mean(float(row["margin"]) for row in done)
                                  if done else None),
        "candidate_schema_violations": sum(int(row.get("candidate_schema_violations", 0))
                                           for row in rows),
        "opponent_schema_violations": sum(int(row.get("opponent_schema_violations", 0))
                                          for row in rows),
        "all_719_calls": planned > 0 and all(row.get("status") == "DONE"
                                             and int(row.get("calls", 0)) == 719
                                             for row in rows),
    }


def metric_delta(variant: Mapping[str, Any], base: Mapping[str, Any], name: str) -> float | None:
    if variant.get("status") != "DONE" or base.get("status") != "DONE":
        return None
    return float(variant[name]) - float(base[name])


def paired_rows(rows: Sequence[Mapping[str, Any]], variants: Sequence[str]) -> list[dict[str, Any]]:
    index = {(row["variant_id"], row["opponent"], int(row["seed"]),
              int(row["candidate_seat"])): row for row in rows}
    pairs: list[dict[str, Any]] = []
    contexts = sorted({(row["opponent"], int(row["seed"]), int(row["candidate_seat"]))
                       for row in rows})
    for variant in variants:
        if variant == "base":
            continue
        for opponent, seed, seat in contexts:
            base = index[("base", opponent, seed, seat)]
            current = index[(variant, opponent, seed, seat)]
            complete = base.get("status") == current.get("status") == "DONE"
            pairs.append({
                "variant_id": variant, "base_variant": "base", "opponent": opponent,
                "seed": seed, "candidate_seat": seat,
                "pair_status": "DONE" if complete else "INCOMPLETE_NONWIN",
                "candidate_bank_delta": metric_delta(current, base, "candidate_bank"),
                "opponent_bank_delta": metric_delta(current, base, "opponent_bank"),
                "margin_delta": metric_delta(current, base, "margin"),
                "score_delta": metric_delta(current, base, "score"),
                "win_flip": (int(current["win"]) - int(base["win"]) if complete else 0),
                "first_shop_changed": (current.get("first_shop") != base.get("first_shop")
                                       if complete else None),
                "diagnostics_changed": (hash_value(current.get("diagnostics"))
                                        != hash_value(base.get("diagnostics")) if complete else None),
            })
    return pairs


def synergy_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    index = {(row["variant_id"], row["opponent"], int(row["seed"]),
              int(row["candidate_seat"])): row for row in rows}
    contexts = sorted({(row["opponent"], int(row["seed"]), int(row["candidate_seat"]))
                       for row in rows if row["variant_id"] == "base"})
    output: list[dict[str, Any]] = []
    for opponent, seed, seat in contexts:
        values = {name: index[(name, opponent, seed, seat)] for name in CORE_VARIANTS}
        complete = all(row.get("status") == "DONE" for row in values.values())
        item = {"opponent": opponent, "seed": seed, "candidate_seat": seat,
                "status": "DONE" if complete else "INCOMPLETE_NONWIN"}
        for metric in ("candidate_bank", "opponent_bank", "margin", "score"):
            item[f"{metric}_synergy"] = (
                float(values["full"][metric]) - float(values["target_only"][metric])
                - float(values["market_only"][metric]) + float(values["base"][metric])
                if complete else None
            )
        output.append(item)
    return output


def path_coverage(rows: Sequence[Mapping[str, Any]], variants: Sequence[str]) -> dict[str, Any]:
    coverage: dict[str, Any] = {}
    for variant in variants:
        subset = [row for row in rows if row["variant_id"] == variant]
        done = [row for row in subset if row.get("status") == "DONE"]
        def counts(field: str) -> dict[str, int]:
            values = [str((row.get("diagnostics") or {}).get(field, "MISSING")) for row in done]
            return dict(sorted(__import__("collections").Counter(values).items()))
        stage_paths = __import__("collections").Counter()
        market_policy_active = 0
        for row in done:
            diagnostic = row.get("diagnostics") or {}
            for commit in (diagnostic.get("stage_commits") or {}).values():
                if isinstance(commit, Mapping):
                    stage_paths[str(commit.get("path", "MISSING"))] += 1
            if sum(int(value or 0) for value in
                   (diagnostic.get("market_policy_counts") or {}).values()) > 0:
                market_policy_active += 1
        coverage[variant] = {
            "planned": len(subset), "completed": len(done),
            "first_shop": dict(sorted(__import__("collections").Counter(
                str(row.get("first_shop", "MISSING")) for row in done).items())),
            "base_expert": counts("base_expert"),
            "path_leaf": counts("path_leaf"),
            "path_candidate": counts("path_candidate"),
            "collision_product": counts("collision_product"),
            "scarcity_product": counts("scarcity_product"),
            "stage_commit_paths": dict(sorted(stage_paths.items())),
            "market_policy_active_games": market_policy_active,
            "diagnostics_present": sum(bool(row.get("diagnostics")) for row in done),
            "coverage_complete": len(done) == len(subset)
                                 and all(bool(row.get("diagnostics")) for row in done),
        }
    return coverage


def verify_preregistered(manifest_path: Path, tasks_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tasks_payload = json.loads(tasks_path.read_text(encoding="utf-8"))
    tasks = list(tasks_payload["tasks"])
    if manifest.get("schema") != SCHEMA:
        raise ValueError("manifest schema mismatch")
    if tuple(manifest.get("r3_exposed_seeds", [])) != EXPECTED_R3_SEEDS:
        raise ValueError("manifest seed drift")
    if manifest.get("uses_development") or manifest.get("uses_confirmation"):
        raise ValueError("dev/confirmation is forbidden")
    if len(tasks) != int(manifest["planned_games"]):
        raise ValueError("planned denominator drift")
    task_hash = hash_value([
        {key: task[key] for key in ("task_id", "cache_key", "variant_spec_hash",
                                    "opponent_hash", "seed", "candidate_seat", "mode")}
        for task in tasks
    ])
    if task_hash != manifest["task_plan_sha256"]:
        raise ValueError("task plan hash drift")
    current, current_tasks = plan(Path(manifest["source_hashes"]["candidate_path"]),
                                  bool(manifest["include_fixed_paths"]),
                                  int(manifest["workers"]))
    for key in ("param_hash", "r3_exposed_seeds", "gold_opponents", "planned_games",
                "task_plan_sha256", "seed_list_sha256", "source_hashes"):
        if current[key] != manifest[key]:
            raise ValueError(f"preregistered field drift: {key}")
    if hash_value(current_tasks) != hash_value(tasks):
        raise ValueError("frozen task payload drift")
    return manifest, tasks


def run_preregistered(manifest_path: Path, workers: int | None = None) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    output_dir = manifest_path.parent
    tasks_path = output_dir / "tasks.json"
    sidecar = output_dir / "preregistered_manifest.sha256"
    expected_manifest_hash = sidecar.read_text(encoding="utf-8").strip()
    if sha256_file(manifest_path) != expected_manifest_hash:
        raise ValueError("manifest sidecar hash mismatch")
    manifest, tasks = verify_preregistered(manifest_path, tasks_path)
    actual_workers = int(workers if workers is not None else manifest["workers"])
    if not 1 <= actual_workers <= 8:
        raise ValueError("workers must be in [1,8]")
    targets = [output_dir / name for name in
               ("games.jsonl", "paired_results.json", "synergy.json",
                "path_coverage.json", "summary.json")]
    if any(path.exists() for path in targets):
        raise FileExistsError("refusing to overwrite an existing ablation result")
    rows: list[dict[str, Any]] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=actual_workers) as pool:
        pending = {pool.submit(play_task, task): task for task in tasks}
        for future in concurrent.futures.as_completed(pending):
            task = pending[future]
            try:
                rows.append(future.result())
            except BaseException as exc:
                rows.append(error_row(task, f"worker:{type(exc).__name__}: {exc}"))
    order = {task["task_id"]: index for index, task in enumerate(tasks)}
    rows.sort(key=lambda row: order[row["task_id"]])
    with targets[0].open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    variants = [str(item["variant_id"]) for item in manifest["variants"]]
    pairs = paired_rows(rows, variants)
    synergy = synergy_rows(rows)
    coverage = path_coverage(rows, variants)
    atomic_json(targets[1], {"schema": "v116-rc9-ablation-pairs-v1", "pairs": pairs})
    atomic_json(targets[2], {"schema": "v116-rc9-ablation-synergy-v1", "rows": synergy})
    atomic_json(targets[3], {"schema": "v116-rc9-ablation-path-coverage-v1",
                             "variants": coverage})
    by_variant = {variant: aggregate([row for row in rows if row["variant_id"] == variant])
                  for variant in variants}
    overall = aggregate(rows)
    mechanics_ok = (overall["completed_games"] == manifest["planned_games"]
                    and overall["all_719_calls"]
                    and overall["candidate_schema_violations"] == 0
                    and len(pairs) == manifest["planned_base_pairs"]
                    and len(synergy) == manifest["planned_synergy_rows"]
                    and all(item["pair_status"] == "DONE" for item in pairs)
                    and all(item["status"] == "DONE" for item in synergy))
    summary = {
        "schema": "v116-rc9-ablation-summary-v1",
        "purpose": "mechanism_ablation_only_not_advancement",
        "run_fingerprint": manifest["run_fingerprint"],
        "overall": overall, "by_variant": by_variant,
        "path_coverage": coverage,
        "pair_rows": len(pairs), "synergy_rows": len(synergy),
        "mechanics_ok": mechanics_ok,
        "hashes": {
            "preregistered_manifest_sha256": sha256_file(manifest_path),
            "tasks_sha256": sha256_file(tasks_path),
            "task_plan_sha256": manifest["task_plan_sha256"],
            "seed_list_sha256": manifest["seed_list_sha256"],
            "source_hashes_sha256": hash_value(manifest["source_hashes"]),
            "games_sha256": sha256_file(targets[0]),
            "paired_results_sha256": sha256_file(targets[1]),
            "synergy_sha256": sha256_file(targets[2]),
            "path_coverage_sha256": sha256_file(targets[3]),
            "candidate_action_trace_manifest_sha256": hash_value([
                [row["task_id"], row.get("candidate_action_sha256")] for row in rows
            ]),
            "opponent_action_trace_manifest_sha256": hash_value([
                [row["task_id"], row.get("opponent_action_sha256")] for row in rows
            ]),
            "diagnostic_trace_manifest_sha256": hash_value([
                [row["task_id"], hash_value(row.get("diagnostic_trace", []))] for row in rows
            ]),
        },
        "decision": "ABLATION_MECHANISM_DIAGNOSTIC_ONLY",
        "gold_evidence": False,
    }
    atomic_json(targets[4], summary)
    return summary


def write_plan(output_dir: Path, manifest: Mapping[str, Any],
               tasks: Sequence[Mapping[str, Any]]) -> None:
    output_dir = output_dir.expanduser().resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    manifest_path = output_dir / "preregistered_manifest.json"
    tasks_path = output_dir / "tasks.json"
    atomic_json(manifest_path, manifest)
    atomic_json(tasks_path, {"schema": "v116-rc9-ablation-task-plan-v1", "tasks": list(tasks)})
    (output_dir / "preregistered_manifest.sha256").write_text(
        sha256_file(manifest_path) + "\n", encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    plan_parser = commands.add_parser("plan")
    plan_parser.add_argument("--candidate", type=Path, required=True)
    plan_parser.add_argument("--output-dir", type=Path, required=True)
    plan_parser.add_argument("--include-fixed", action="store_true")
    plan_parser.add_argument("--workers", type=int, default=8)
    plan_parser.add_argument("--dry-run", action="store_true")
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--manifest", type=Path, required=True)
    run_parser.add_argument("--workers", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "plan":
        manifest, tasks = plan(args.candidate, args.include_fixed, args.workers)
        if args.dry_run:
            print(json.dumps({"dry_run": True, "writes": False, "manifest": manifest,
                              "task_count": len(tasks)}, ensure_ascii=False, indent=2))
        else:
            write_plan(args.output_dir, manifest, tasks)
            print(json.dumps({"preregistered": True,
                              "manifest": str(args.output_dir / "preregistered_manifest.json"),
                              "planned_games": len(tasks)}, ensure_ascii=False, indent=2))
        return 0
    summary = run_preregistered(args.manifest, args.workers)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CORE_VARIANTS", "FIXED_VARIANTS", "EXPECTED_GOLD", "EXPECTED_R3_SEEDS",
    "aggregate", "build_tasks", "paired_rows", "path_coverage", "plan",
    "run_preregistered", "synergy_rows", "variant_specs", "write_plan",
    "validate_variant_contract",
]
