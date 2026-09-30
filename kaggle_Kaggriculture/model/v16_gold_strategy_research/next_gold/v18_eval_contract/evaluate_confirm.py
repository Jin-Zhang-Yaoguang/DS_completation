#!/usr/bin/env python3
"""Fail-closed, preregistered V18 P0 confirmation evaluator.

This evaluator never imports candidate development code.  It consumes only a
frozen Kaggle archive plus its manifest and compares it with the frozen V17
archive on identical opponent-family, seed, and seat blocks.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import random
import re
import statistics
import sys
import tarfile
import uuid
from collections import Counter, defaultdict
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[5]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
INDEX = ROOT / "kaggle_Kaggriculture" / "model_data" / "kaggriculture_episodes_index"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
LIVE_REPAIR = MODEL / "v1_adaptive_market" / "main.py"
OFFICIAL_RULES = MODEL / "v15_cleanroom_search" / "cleanroom" / "sessions" / "attempt_002" / "official_rules" / "kaggriculture.py"
REDTEAM = MODEL / "v16_gold_strategy_research" / "portfolio_redteam" / "redteam_audit.py"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(path: Path, prefix: str):
    name = f"{prefix}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runtime(contract: dict[str, Any]):
    import kaggle_environments
    from kaggle_environments.envs.kaggriculture import kaggriculture as installed_rules

    if str(kaggle_environments.__version__) != contract["runtime"]["kaggle_environments_version"]:
        raise RuntimeError(f"kaggle-environments drift: {kaggle_environments.__version__}")
    builds = sorted((CPPSIM / "build").glob("lib.*/kagsim*.so"))
    if len(builds) != 1:
        raise RuntimeError(f"expected one cppsim extension, got {builds}")
    if sha256(builds[0]) != contract["runtime"]["cppsim_extension_sha256"]:
        raise RuntimeError("cppsim extension SHA drift")
    if sha256(OFFICIAL_RULES) != contract["runtime"]["official_rules_sha256"]:
        raise RuntimeError("official rules SHA drift")
    if sha256(Path(installed_rules.__file__)) != contract["runtime"]["official_rules_sha256"]:
        raise RuntimeError("installed official rules SHA drift")
    sys.path[:0] = [str(builds[0].parent), str(FACTORY)]
    import kagsim  # type: ignore

    if str(kagsim.ENGINE_VERSION) != contract["runtime"]["cppsim_engine_version"]:
        raise RuntimeError(f"cppsim engine drift: {kagsim.ENGINE_VERSION}")
    return kagsim


def archive_source(path: Path, expected_archive_sha: str, expected_main_sha: str) -> str:
    if sha256(path) != expected_archive_sha:
        raise RuntimeError(f"archive SHA mismatch: {path}")
    with tarfile.open(path, "r:gz") as tar:
        members = tar.getmembers()
        names = [member.name for member in members if member.isfile()]
        if names != ["main.py"]:
            raise RuntimeError(f"archive must contain exactly main.py, got {names}")
        member = members[names.index("main.py")]
        extracted = tar.extractfile(member)
        if extracted is None:
            raise RuntimeError("cannot read main.py")
        payload = extracted.read()
    if sha256_bytes(payload) != expected_main_sha:
        raise RuntimeError(f"main.py SHA mismatch: {path}")
    return payload.decode("utf-8")


def validate_candidate_manifest(path: Path, contract: dict[str, Any]) -> tuple[dict[str, Any], Path, str]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "candidate", "archive", "archive_sha256", "main_sha256", "frozen_at",
        "development_direct_replay_dates", "development_seeds", "confirm_data_accessed_before_freeze",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise RuntimeError(f"candidate manifest missing {missing}")
    if manifest["candidate"] not in contract["multiplicity"]["candidates"]:
        raise RuntimeError("unregistered candidate name")
    allowed_dates = set(contract["data_partition"]["development_allowed_direct_replay_dates"])
    dev_dates = set(manifest["development_direct_replay_dates"])
    confirm_dates = set(contract["data_partition"]["confirmation_replay_dates"])
    if not dev_dates <= allowed_dates or dev_dates & confirm_dates:
        raise RuntimeError(f"development/confirmation date leakage: {sorted(dev_dates & confirm_dates)}")
    low, high = contract["data_partition"]["development_allowed_seed_range"]
    dev_seeds = {int(seed) for seed in manifest["development_seeds"]}
    confirm_low, confirm_high = contract["data_partition"]["confirmation_seed_range"]
    confirm_seeds = set(range(confirm_low, confirm_high + 1))
    if any(seed < low or seed > high for seed in dev_seeds) or dev_seeds & confirm_seeds:
        raise RuntimeError("development/confirmation seed leakage")
    if manifest["confirm_data_accessed_before_freeze"] is not False:
        raise RuntimeError("candidate declares confirm access before freeze")
    archive = Path(manifest["archive"])
    if not archive.is_absolute():
        archive = (path.parent / archive).resolve()
    source = archive_source(archive, manifest["archive_sha256"], manifest["main_sha256"])
    forbidden_tokens = [
        *contract["data_partition"]["confirmation_replay_dates"],
        *(str(item["episode"]) for item in contract["opponent_selection"]["families"]),
    ]
    hits = [token for token in forbidden_tokens if re.search(rf"(?<![0-9A-Za-z_]){re.escape(token)}(?![0-9A-Za-z_])", source)]
    if hits:
        raise RuntimeError(f"candidate source contains confirm-only literal(s): {hits}")
    return manifest, archive, source


def semantic_signature(actions: list[dict[str, Any]]) -> str:
    crops = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
    animals = ("GOOSE", "COW", "SHEEP")
    buys = {key: 0 for key in (*crops, *animals)}
    plants = {key: 0 for key in crops}
    ops: Counter[str] = Counter()
    for action in actions:
        for order in [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]:
            op = str(order[0]) if order else "PASS"
            ops[op] += 1
            if op == "PLANT" and len(order) >= 2 and order[1] in plants:
                plants[order[1]] += 1
        for order in action.get("market") or []:
            if not order:
                continue
            op = str(order[0])
            ops[op] += 1
            if op in {"BUY_SEED", "BUY_ANIMAL"} and len(order) >= 3 and order[1] in buys:
                buys[order[1]] += max(0, int(order[2] or 0))
    descriptor = {
        "buy_totals": buys,
        "plant_counts": plants,
        "land_requests": ops["BUY_LAND"],
        "hire_requests": ops["HIRE"],
        "animal_care": [ops["FEED"], ops["CARE"]],
        "prefix_exact_sha256": hashlib.sha256(
            json.dumps(actions[:72], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    return hashlib.sha256(json.dumps(descriptor, sort_keys=True).encode()).hexdigest()


def load_families(contract: dict[str, Any]) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    result = []
    signatures = set()
    for item in contract["opponent_selection"]["families"]:
        path = INDEX / f"date={item['date']}" / "data" / f"{item['episode']}.json"
        if sha256(path) != item["replay_sha256"]:
            raise RuntimeError(f"replay SHA mismatch: {path}")
        replay = json.loads(path.read_text(encoding="utf-8"))
        if int(replay["info"]["EpisodeId"]) != int(item["episode"]) or item["team"] not in replay["info"]["TeamNames"]:
            raise RuntimeError(f"replay identity mismatch: {path}")
        seat = replay["info"]["TeamNames"].index(item["team"])
        actions = [copy.deepcopy(pair[seat].get("action") or {}) for pair in replay["steps"][1:720]]
        signature = semantic_signature(actions)
        if signature != item["behavior_signature"] or signature in signatures:
            raise RuntimeError(f"behavior signature mismatch/duplicate: {item['team']}")
        signatures.add(signature)
        meta = dict(item)
        meta["family"] = f"{item['date']}::{item['team']}::{signature[:12]}"
        result.append((meta, actions))
    return result


def raw_factory(source: str, path_hint: Path) -> tuple[str, Callable[[], Callable]]:
    from kaggle_environments.agent import get_last_callable

    selected = get_last_callable(source, path=str(path_hint))
    selected_name = getattr(selected, "__name__", "")

    def fresh():
        return get_last_callable(source, path=str(path_hint))

    return selected_name, fresh


def opponent_factory(actions: list[dict[str, Any]]) -> Callable[[], Callable]:
    def fresh():
        base = load_module(LIVE_REPAIR, "v18_confirm_proxy")

        def policy(obs, configuration=None):
            del configuration
            base._ACTIONS = actions
            return base._CORE_AGENT(obs)

        return policy

    return fresh


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def tails(margins: list[float]) -> dict[str, float]:
    ordered = sorted(margins)
    count = max(1, math.ceil(0.10 * len(ordered)))
    return {"p10": quantile(ordered, 0.10), "cvar10": statistics.mean(ordered[:count])}


def audit_helpers():
    module = load_module(REDTEAM, "v18_confirm_audit")
    return module._audit_action


def dry_market_audit(
    observations: list[dict[str, Any]], actions: list[dict[str, Any]], seat: int,
    counts: Counter, failures: list[dict[str, Any]], seed: int,
) -> None:
    """Run the official unit+market transaction code on copies and count every fill.

    This catches failed SELL/BUY_PRODUCT/BUY_ANIMAL in addition to land, hire,
    and seed failures.  The installed rule file is SHA-locked before this is
    called, so this is the same transaction code used by official 1.32.7.
    """
    from kaggle_environments.envs.kaggriculture import kaggriculture as rules

    farms = copy.deepcopy(observations[0]["farms"])
    privates = [copy.deepcopy(observations[player]["private"]) for player in (0, 1)]
    day = int(observations[0]["day"])
    turns_per_day = 24
    board_size = len(farms[0]["tiles"])
    shed_capacity = 100
    for player in (0, 1):
        action = actions[player] if isinstance(actions[player], dict) else {}
        unit_orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
        # Mirror the interpreter's atomic PLANT guard.
        demand = Counter(order[1] for order in unit_orders if isinstance(order, list) and len(order) >= 2 and order[0] == "PLANT")
        blocked = {crop for crop, amount in demand.items() if amount > int(privates[player]["seeds"].get(crop, 0) or 0)}
        for index, order in enumerate(unit_orders):
            applied = ["PASS"] if isinstance(order, list) and len(order) >= 2 and order[0] == "PLANT" and order[1] in blocked else order
            rules._apply_unit_action(farms[player], privates[player], index, applied, board_size, day, turns_per_day, shed_capacity)

    candidate_orders = actions[seat].get("market") or []
    requested: Counter = Counter()
    for index, order in enumerate(candidate_orders):
        if index >= 10:
            requested["MARKET_OVERFLOW"] += 1
            continue
        parsed = rules._parse_order(order)
        if parsed is None:
            requested["MALFORMED"] += 1
        elif parsed["type"] in {"HIRE", "BUY_LAND"}:
            requested[parsed["type"]] += 1
        else:
            requested[f"{parsed['type']}::{parsed['item']}"] += int(parsed["remaining"])
    successful: Counter = Counter()
    original_commit = rules._commit_unit
    original_hire = rules._do_hire
    original_land = rules._do_buy_land

    def traced_commit(op, item, price, farm, private, market, shed_capacity=100):
        ok = original_commit(op, item, price, farm, private, market, shed_capacity)
        if farm is farms[seat] and ok:
            successful[f"{op}::{item}"] += 1
        return ok

    def traced_hire(farm, private, board_size, mult=rules.FARM_HAND_COST_MULT):
        before = len(farm["hands"])
        result = original_hire(farm, private, board_size, mult)
        if farm is farms[seat] and len(farm["hands"]) > before:
            successful["HIRE"] += 1
        return result

    def traced_land(farm, board_size):
        before = len(farm["unlocked_quadrants"])
        result = original_land(farm, board_size)
        if farm is farms[seat] and len(farm["unlocked_quadrants"]) > before:
            successful["BUY_LAND"] += 1
        return result

    state = []
    for player in (0, 1):
        observation = SimpleNamespace(private=privates[player])
        if player == 0:
            observation.farms = farms
            observation.market = copy.deepcopy(observations[0]["market"])
        state.append(SimpleNamespace(action=actions[player], observation=observation))
    env = SimpleNamespace(configuration={
        "boardSize": board_size, "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1, "shedCapacity": shed_capacity,
    })
    try:
        rules._commit_unit = traced_commit
        rules._do_hire = traced_hire
        rules._do_buy_land = traced_land
        rules._process_market(state, env)
    finally:
        rules._commit_unit = original_commit
        rules._do_hire = original_hire
        rules._do_buy_land = original_land
    for key, amount in requested.items():
        counts[f"market_requested::{key}"] += amount
        counts[f"market_filled::{key}"] += successful[key]
        if successful[key] < amount:
            failures.append({
                "kind": key, "seed": seed, "step": int(observations[seat]["step"]),
                "seat": seat, "requested": amount, "filled": successful[key],
            })


def play_cpp(
    policy_factory: Callable[[], Callable], opponent_builder: Callable[[], Callable], seed: int,
    seat: int, kagsim: Any, audit: bool, audit_action: Callable | None,
) -> tuple[float, float, Counter, list[dict[str, Any]], int, int]:
    policy, opponent = policy_factory(), opponent_builder()
    agents = [policy, opponent] if seat == 0 else [opponent, policy]
    counts: Counter = Counter()
    failures: list[dict[str, Any]] = []
    calls = [0, 0]
    stdout, stderr = StringIO(), StringIO()
    game = kagsim.Game(int(seed))
    with redirect_stdout(stdout), redirect_stderr(stderr):
        while not game.done:
            observations = [game.observe(0), game.observe(1)]
            actions = []
            for player in (0, 1):
                actions.append(agents[player](observations[player]))
                calls[player] += 1
            if audit:
                obs = observations[seat]
                action = actions[seat]
                audit_action(obs, action, counts, failures)
                dry_market_audit(observations, actions, seat, counts, failures, seed)
            game.step(*actions)
    rewards = [float(game.reward(0)), float(game.reward(1))]
    return rewards[seat], rewards[1 - seat], counts, failures, len(stdout.getvalue().encode()), len(stderr.getvalue().encode())


def cluster_bootstrap(rows: list[dict[str, Any]], seeds: list[int], repetitions: int, rng_seed: int) -> list[float]:
    blocks = {seed: [row for row in rows if int(row["seed"]) == seed] for seed in seeds}
    rng = random.Random(rng_seed)
    samples = []
    for _ in range(repetitions):
        sampled = rng.choices(seeds, k=len(seeds))
        selected = [row for seed in sampled for row in blocks[seed]]
        samples.append(100.0 * statistics.mean(row["score_delta"] for row in selected))
    return [quantile(samples, 0.025), quantile(samples, 0.975)]


def official_parity(source: str, candidate_factory: Callable[[], Callable], opponent_builder: Callable[[], Callable], seeds: list[int], kagsim: Any) -> dict[str, Any]:
    import numpy as np
    from kaggle_environments import make

    rows = []
    for seed in seeds:
        for seat in (0, 1):
            cpp_own, cpp_opp, _, _, cpp_out, cpp_err = play_cpp(candidate_factory, opponent_builder, seed, seat, kagsim, False, None)
            random.seed(seed * 104729 + seat)
            np.random.seed((seed + seat * 65537) % (2**32 - 1))
            policy, opponent = candidate_factory(), opponent_builder()
            agents = [policy, opponent] if seat == 0 else [opponent, policy]
            calls = [0, 0]
            wrapped = []
            for index, agent in enumerate(agents):
                def call(obs, configuration=None, agent=agent, index=index):
                    calls[index] += 1
                    return agent(obs, configuration)
                wrapped.append(call)
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
                env.run(wrapped)
            official = [float(state.reward or 0) for state in env.state]
            cpp = [cpp_own, cpp_opp] if seat == 0 else [cpp_opp, cpp_own]
            rows.append({
                "seed": seed, "candidate_seat": seat, "cpp_rewards": cpp, "official_rewards": official,
                "exact": cpp == official, "calls": calls, "statuses": [str(state.status) for state in env.state],
                "stdout_bytes": cpp_out + len(stdout.getvalue().encode()),
                "stderr_bytes": cpp_err + len(stderr.getvalue().encode()),
            })
    return {"games": len(rows), "exact_games": sum(row["exact"] for row in rows), "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed-limit", type=int)
    parser.add_argument("--family-limit", type=int)
    parser.add_argument("--bootstrap-reps", type=int)
    args = parser.parse_args()

    lock = json.loads((HERE / "LOCK.json").read_text(encoding="utf-8"))
    actual_contract_sha = sha256(HERE / "contract.json")
    actual_evaluator_sha = sha256(Path(__file__).resolve())
    if actual_contract_sha != lock["contract_sha256"] or actual_evaluator_sha != lock["evaluator_sha256"]:
        raise RuntimeError("preregistered contract/evaluator lock mismatch")
    contract = json.loads((HERE / "contract.json").read_text(encoding="utf-8"))
    kagsim = runtime(contract)
    manifest, candidate_archive, candidate_source = validate_candidate_manifest(args.candidate_manifest, contract)
    parent_archive = (HERE / contract["parent"]["archive"]).resolve()
    parent_source = archive_source(parent_archive, contract["parent"]["archive_sha256"], contract["parent"]["main_sha256"])
    selected_name, candidate_factory = raw_factory(candidate_source, candidate_archive)
    parent_name, parent_factory = raw_factory(parent_source, parent_archive)
    families = load_families(contract)
    if args.family_limit:
        families = families[:args.family_limit]
    low, high = contract["data_partition"]["confirmation_seed_range"]
    seeds = list(range(low, high + 1))
    if args.seed_limit:
        seeds = seeds[:args.seed_limit]
    full_run = len(seeds) == high - low + 1 and len(families) == len(contract["opponent_selection"]["families"])
    audit_action = audit_helpers()
    rows = []
    parent_audit_counts: Counter = Counter()
    candidate_audit_counts: Counter = Counter()
    parent_failures: list[dict[str, Any]] = []
    candidate_failures: list[dict[str, Any]] = []
    output_bytes = {"stdout": 0, "stderr": 0}
    for family_index, (meta, actions) in enumerate(families, 1):
        opponent_builder = opponent_factory(actions)
        for seed in seeds:
            for seat in (0, 1):
                parent_own, parent_opp, parent_counts, parent_game_failures, parent_out, parent_err = play_cpp(parent_factory, opponent_builder, seed, seat, kagsim, True, audit_action)
                candidate_own, candidate_opp, candidate_counts, candidate_game_failures, candidate_out, candidate_err = play_cpp(candidate_factory, opponent_builder, seed, seat, kagsim, True, audit_action)
                parent_audit_counts.update(parent_counts)
                candidate_audit_counts.update(candidate_counts)
                parent_failures.extend(parent_game_failures)
                candidate_failures.extend(candidate_game_failures)
                output_bytes["stdout"] += parent_out + candidate_out
                output_bytes["stderr"] += parent_err + candidate_err
                parent_margin = parent_own - parent_opp
                candidate_margin = candidate_own - candidate_opp
                rows.append({
                    "family": meta["family"], "seed": seed, "seat": seat,
                    "parent_own": parent_own, "parent_opp": parent_opp, "parent_margin": parent_margin,
                    "candidate_own": candidate_own, "candidate_opp": candidate_opp, "candidate_margin": candidate_margin,
                    "parent_score": score(parent_margin), "candidate_score": score(candidate_margin),
                    "score_delta": score(candidate_margin) - score(parent_margin),
                    "margin_delta": candidate_margin - parent_margin,
                    "parent_resource_action_failures": len(parent_game_failures),
                    "candidate_resource_action_failures": len(candidate_game_failures),
                    "resource_action_failure_delta": len(candidate_game_failures) - len(parent_game_failures),
                })
        print(json.dumps({"progress_family": family_index, "families": len(families), "rows": len(rows)}), flush=True)

    repetitions = args.bootstrap_reps or contract["statistics"]["bootstrap_repetitions"]
    score_uplift = 100.0 * statistics.mean(row["score_delta"] for row in rows)
    ci = cluster_bootstrap(rows, seeds, repetitions, contract["statistics"]["bootstrap_rng_seed"])
    family_uplift = {
        family: 100.0 * statistics.mean(row["score_delta"] for row in rows if row["family"] == family)
        for family in sorted({row["family"] for row in rows})
    }
    parent_tail = tails([row["parent_margin"] for row in rows])
    candidate_tail = tails([row["candidate_margin"] for row in rows])
    parity = official_parity(
        candidate_source, candidate_factory, opponent_factory(families[0][1]),
        contract["data_partition"]["official_parity_seeds"], kagsim,
    )
    gates = contract["promotion_gates"]
    candidate_kind = manifest["candidate"]
    resource_absolute_zero = len(candidate_failures) == 0
    resource_total_noninferior = len(candidate_failures) <= len(parent_failures)
    resource_each_game_noninferior = all(row["resource_action_failure_delta"] <= 0 for row in rows)
    resource_scope_pass = resource_absolute_zero if candidate_kind in {"market_mpc", "combined"} else (
        resource_total_noninferior and resource_each_game_noninferior
    )
    checks = {
        "full_preregistered_panel": full_run,
        "paired_score_uplift": score_uplift >= gates["paired_score_uplift_pp_min"],
        "cluster95_lower": ci[0] > gates["paired_score_uplift_cluster95_lower_strictly_greater_than_pp"],
        "each_family_noninferior": min(family_uplift.values()) >= gates["each_family_score_uplift_pp_min"],
        "p10_noninferior": candidate_tail["p10"] - parent_tail["p10"] >= gates["candidate_margin_p10_minus_parent_min"],
        "cvar10_noninferior": candidate_tail["cvar10"] - parent_tail["cvar10"] >= gates["candidate_margin_cvar10_minus_parent_min"],
        "unit_actions_valid": candidate_audit_counts["unit_invalid"] <= gates["unit_action_precondition_failures_max"],
        "audited_resources_scope_gate": resource_scope_pass,
        "raw_loader": selected_name == gates["raw_loader_selected_callable"] and parent_name == "agent",
        "silent": output_bytes["stdout"] <= gates["stdout_bytes_max"] and output_bytes["stderr"] <= gates["stderr_bytes_max"],
        "official_cpp_parity": parity["exact_games"] == parity["games"] and all(
            row["calls"] == [gates["calls_per_agent"], gates["calls_per_agent"]]
            and row["statuses"] == gates["official_statuses"]
            and row["stdout_bytes"] == 0 and row["stderr_bytes"] == 0
            for row in parity["rows"]
        ),
    }
    result = {
        "status": "CONFIRM" if full_run else "SMOKE_ONLY",
        "decision": "PASS" if all(checks.values()) else "FAIL",
        "contract_version": contract["contract_version"],
        "preregistration_lock": {
            "contract_sha256": actual_contract_sha,
            "evaluator_sha256": actual_evaluator_sha,
        },
        "candidate": manifest,
        "parent": contract["parent"],
        "engine": str(kagsim.ENGINE_VERSION),
        "panel": {"families": len(families), "seeds": seeds, "both_seats": True, "paired_games": len(rows)},
        "paired": {
            "score_uplift_pp": score_uplift, "score_uplift_seed_cluster95_pp": ci,
            "margin_delta_mean": statistics.mean(row["margin_delta"] for row in rows),
            "score_positive_zero_negative": [sum(row["score_delta"] > 0 for row in rows), sum(row["score_delta"] == 0 for row in rows), sum(row["score_delta"] < 0 for row in rows)],
            "by_family_score_uplift_pp": family_uplift,
        },
        "tails": {
            "parent": parent_tail, "candidate": candidate_tail,
            "candidate_minus_parent": {key: candidate_tail[key] - parent_tail[key] for key in parent_tail},
        },
        "action_resource_audit": {
            "coverage": "all unit preconditions and exact official-rule dry-run fills for SELL, BUY_PRODUCT, BUY_SEED, BUY_ANIMAL, BUY_LAND, HIRE, malformed and overflow orders",
            "scope_policy": gates["resource_scope_policy"][candidate_kind],
            "parent": {
                "counts": dict(parent_audit_counts), "failure_count": len(parent_failures),
                "failure_examples": parent_failures[:50],
            },
            "candidate": {
                "counts": dict(candidate_audit_counts), "failure_count": len(candidate_failures),
                "failure_examples": candidate_failures[:50],
            },
            "candidate_minus_parent_failure_count": len(candidate_failures) - len(parent_failures),
            "paired_games_candidate_noninferior": sum(row["resource_action_failure_delta"] <= 0 for row in rows),
            "paired_games_total": len(rows),
            "resource_subchecks": {
                "candidate_absolute_zero": resource_absolute_zero,
                "candidate_total_noninferior": resource_total_noninferior,
                "candidate_each_game_noninferior": resource_each_game_noninferior,
            },
        },
        "raw_output_bytes": output_bytes,
        "raw_loader": {"candidate": selected_name, "parent": parent_name},
        "official_parity": parity,
        "checks": checks,
        "bootstrap": {"cluster": "environment_seed", "repetitions": repetitions, "rng_seed": contract["statistics"]["bootstrap_rng_seed"]},
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "decision", "panel", "paired", "tails", "checks")}, ensure_ascii=False, indent=2))
    return 0 if result["decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
