#!/usr/bin/env python3
"""Frozen 4-seed dual-seat RC6 regression panel."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
CPPSIM = (MODEL / "community_research" / "2026-08-26" / "live_cli" /
          "external_repos" / "kaggriculture-cppsim")
sys.path.insert(0, str(HERE))
import main as policy  # noqa: E402


def _load_cppsim() -> Any:
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError("cppsim build missing")
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    return kagsim


KAGSIM = _load_cppsim()


def asset_metrics(executor: policy.ShopRouterExecutor, obs: dict[str, Any], seat: int) -> dict[str, Any]:
    farm = obs["farms"][seat]
    goal = executor.goal(int(obs.get("day", 0) or 0))
    crops, animals, _structures = policy._counts(farm["tiles"])
    numerator = min(len(farm.get("unlocked_quadrants", []) or []), int(goal["lands"]))
    denominator = int(goal["lands"])
    for kind, target in goal["crops"].items():
        numerator += min(crops[kind], int(target))
        denominator += int(target)
    for kind, target in goal["animals"].items():
        numerator += min(animals[kind], int(target))
        denominator += int(target)
    return {
        "realization": numerator / max(1, denominator),
        "productive_assets": sum(crops.values()) + sum(animals.values()),
        "crops": dict(crops),
        "animals": dict(animals),
        "target_crops": sum(int(value) for value in goal["crops"].values()),
        "target_animals": sum(int(value) for value in goal["animals"].values()),
    }


def play(task: tuple[int, int]) -> dict[str, Any]:
    seed, seat = task
    game = KAGSIM.Game(seed)
    executor = policy.ShopRouterExecutor()
    daily: list[dict[str, Any]] = []
    latency: list[int] = []
    schema_errors = 0
    minimum_cash = float("inf")
    max_assets = 0
    while not game.done:
        obs = game.observe(seat)
        farm = obs["farms"][seat]
        minimum_cash = min(minimum_cash, float(farm.get("money", 0) or 0))
        if int(obs.get("hour", 0) or 0) == 23:
            metrics = asset_metrics(executor, obs, seat)
            daily.append(metrics)
            max_assets = max(max_assets, int(metrics["productive_assets"]))
        start = time.perf_counter_ns()
        action = executor.act(obs)
        latency.append(time.perf_counter_ns() - start)
        if (set(action) != {"farmer", "hands", "market"}
                or len(action["hands"]) != len(farm.get("hands", []) or [])
                or len(action["market"]) > 10):
            schema_errors += 1
        pair = [{}, {}]
        pair[seat] = action
        game.step(pair[0], pair[1])
    final = asset_metrics(executor, game.observe(seat), seat)
    return {
        "seed": seed,
        "seat": seat,
        "bank": float(game.reward(seat)),
        "idle_bank": float(game.reward(1 - seat)),
        "pure_win": bool(game.reward(seat) > game.reward(1 - seat)),
        "calls": int(executor.audit["calls"]),
        "schema_errors": schema_errors,
        "minimum_cash": minimum_cash,
        "router_expert": executor.expert,
        "router_commit_step": executor.commit_step,
        "first_visible_shops": list(executor.first_shops),
        "mean_daily_target_realization": statistics.mean(row["realization"] for row in daily),
        "minimum_daily_target_realization": min(row["realization"] for row in daily),
        "final_observed_day_target_realization": daily[-1]["realization"],
        "mean_absolute_productive_assets": statistics.mean(row["productive_assets"] for row in daily),
        "maximum_absolute_productive_assets": max_assets,
        "final_absolute_productive_assets": final["productive_assets"],
        "final_crops": final["crops"],
        "final_animals": final["animals"],
        "final_target_crops": final["target_crops"],
        "final_target_animals": final["target_animals"],
        "mean_latency_us": statistics.mean(latency) / 1000,
        "max_latency_us": max(latency) / 1000,
        "action_audit": dict(executor.audit),
    }


def mechanism_probe() -> dict[str, Any]:
    """Deterministic state probes for the bounded replacement contract."""

    def executor(shop: str = "PET_CAFE") -> policy.ShopRouterExecutor:
        value = policy.ShopRouterExecutor()
        value.expert = "balanced_root"
        value.committed = True
        value.first_shops = (shop,)
        value.balanced_genome = policy.project_balanced(shop)
        return value

    def crop_tile(crop: str) -> dict[str, Any]:
        return {"kind": "PLANT", "crop": crop, "planted_day": 20,
                "yield_units": policy.CROPS[crop]["max_yield"], "watered_today": True}

    pet = executor()
    grid = [[None for _ in range(10)] for _ in range(10)]
    grid[0][0] = crop_tile("CARROT")
    pet._record_replacement_claims(100, 27, 4, grid, [(0, 0)], [["HARVEST"]])
    eligible_claim_created = pet.replacement_claims.get((0, 0), {}).get("crop") == "CARROT"
    empty_grid = [[None for _ in range(10)] for _ in range(10)]
    pet._reconcile_replacement_claims(106, empty_grid, pet.goal(27))
    ttl_cleared = not pet.replacement_claims and pet.audit["replacement_clear_ttl"] == 1

    wrong_crop = executor()
    wrong_grid = [[None for _ in range(10)] for _ in range(10)]
    wrong_grid[0][0] = crop_tile("WHEAT")
    wrong_crop._record_replacement_claims(100, 27, 4, wrong_grid, [(0, 0)], [["HARVEST"]])
    non_demand_rejected = not wrong_crop.replacement_claims

    non_balanced = executor("BAKERY")
    non_balanced.expert = "wool"
    non_balanced._record_replacement_claims(100, 27, 4, wrong_grid, [(0, 0)], [["HARVEST"]])
    non_balanced_rejected = not non_balanced.replacement_claims

    bounded = executor()
    bounded_grid = [[None for _ in range(10)] for _ in range(10)]
    for x in range(3):
        bounded_grid[0][x] = crop_tile("CARROT")
    bounded._record_replacement_claims(
        100, 27, 4, bounded_grid, [(0, 0), (1, 0), (2, 0)],
        [["HARVEST"], ["HARVEST"], ["HARVEST"]],
    )
    live_and_daily_caps_hold = (
        len(bounded.replacement_claims) == 2
        and bounded.replacement_new_by_day[27] == 2
    )

    too_late_regular = executor()
    too_late_regular._record_replacement_claims(
        100, 28, 4, grid, [(0, 0)], [["HARVEST"]]
    )
    finishability_rejected = not too_late_regular.replacement_claims

    terminal = executor()
    terminal_grid = [[None for _ in range(10)] for _ in range(10)]
    terminal_grid[0][0] = crop_tile("CARROT")
    terminal_grid[0][1] = crop_tile("CARROT")
    terminal._record_replacement_claims(
        714, 29, 18, terminal_grid, [(0, 0), (1, 0)], [["HARVEST"], ["HARVEST"]]
    )
    single_terminal_claim = (
        len(terminal.replacement_claims) == 1
        and terminal.audit["replacement_terminal_claim_created"] == 1
    )
    late_jobs = terminal._jobs(
        29, 19, terminal_grid, terminal.goal(29), {crop: 0 for crop in policy.CROPS},
        terminal.goal(29),
    )
    late_terminal_harvest_blocked = not any(
        job[3][0] == "HARVEST" and (job[1], job[2]) in {(0, 0), (1, 0)}
        for job in late_jobs
    )
    results = {
        "eligible_claim_created": eligible_claim_created,
        "ttl_cleared_at_six_steps": ttl_cleared,
        "non_demand_crop_rejected": non_demand_rejected,
        "non_balanced_expert_rejected": non_balanced_rejected,
        "max_live_and_daily_caps_hold": live_and_daily_caps_hold,
        "finishability_gate_rejects_day28_carrot": finishability_rejected,
        "day29_single_terminal_claim": single_terminal_claim,
        "day29_after18_low_asset_harvest_blocked": late_terminal_harvest_blocked,
    }
    return {"checks": results, "pass": all(results.values())}


def originality_audit() -> dict[str, Any]:
    source_path = HERE / "main.py"
    source = source_path.read_text()
    tree = ast.parse(source)
    largest_literal = max((len(node.elts) for node in ast.walk(tree)
                           if isinstance(node, (ast.List, ast.Tuple))), default=0)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = [name for name in imports if any(marker in name.lower() for marker in
                 ("replay", "executor", "compiler", "v19", "v20", "v21", "v76", "labor_planner"))]
    initial = KAGSIM.Game(99117).observe(0)
    poor = copy.deepcopy(initial)
    poor["farms"][0]["money"] = 250
    rich_action = policy.ShopRouterExecutor().act(initial)
    poor_action = policy.ShopRouterExecutor().act(poor)
    mappings = {
        "empty": policy.route_expert([]),
        "yarn": policy.route_expert(["YARN_STORE"]),
        "smoothie": policy.route_expert(["SMOOTHIE_SHOP"]),
        "ice_cream": policy.route_expert(["ICE_CREAM_SHOP"]),
        "pizza": policy.route_expert(["PIZZA_SHOP"]),
        "farmers": policy.route_expert(["FARMERS_MARKET"]),
        "bakery": policy.route_expert(["BAKERY"]),
    }
    final_crop_targets = {name: sum(policy.daily_goal(genome, 29)["crops"].values())
                          for name, genome in policy.GENOMES.items()}
    pet = policy.daily_goal(policy.project_balanced("PET_CAFE"), 29)["crops"]
    projection_targets = {
        shop: policy.daily_goal(policy.project_balanced(shop), 29)["crops"]
        for shop in (*policy.BALANCED_PROJECTIONS, "UNKNOWN_SHOP")
    }
    mapping_pass = mappings == {
        "empty": "balanced_root", "yarn": "wool", "smoothie": "dairy_berry",
        "ice_cream": "dairy_berry", "pizza": "tomato_crop",
        "farmers": "tomato_crop", "bakery": "balanced_root",
    }
    passed = (not policy.validate_genomes() and len(policy.GENOMES) >= 4
              and all(len(policy.compile_daily_goals(value)) == 30 for value in policy.GENOMES.values())
              and min(final_crop_targets.values()) >= 59 and not forbidden
              and largest_literal <= 30 and rich_action != poor_action and mapping_pass
              and pet == {"WHEAT": 24, "MELON": 15, "STRAWBERRY": 9, "CARROT": 11}
              and all(sum(target.values()) == 59 for target in projection_targets.values())
              and all(target.get("WHEAT", 0) >= 18 and target.get("MELON", 0) >= 12
                      and target.get("STRAWBERRY", 0) >= 6
                      for target in projection_targets.values())
              and policy.ENABLE_STAGING is False and policy.ENABLE_PROJECTION is True
              and policy.MAX_LIVE_REPLACEMENT_CLAIMS == 2
              and policy.MAX_NEW_REPLACEMENT_CLAIMS_PER_DAY == 2
              and policy.REPLACEMENT_CLAIM_TTL_STEPS == 6
              and "_ACTIONS" not in source)
    return {
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "genome_count": len(policy.GENOMES),
        "daily_records_per_genome": 30,
        "final_crop_targets": final_crop_targets,
        "balanced_projection_targets": projection_targets,
        "largest_list_or_tuple_literal": largest_literal,
        "forbidden_imports": forbidden,
        "money_perturbation_changes_action": rich_action != poor_action,
        "router_mapping": mappings,
        "router_mapping_pass": mapping_pass,
        "pass": passed,
        "staging_permanently_disabled": policy.ENABLE_STAGING is False,
        "projection_enabled": policy.ENABLE_PROJECTION is True,
        "max_live_replacement_claims": policy.MAX_LIVE_REPLACEMENT_CLAIMS,
        "max_new_replacement_claims_per_day": policy.MAX_NEW_REPLACEMENT_CLAIMS_PER_DAY,
        "replacement_claim_ttl_steps": policy.REPLACEMENT_CLAIM_TTL_STEPS,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=7100)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=HERE / "regression_results.json")
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        raise SystemExit("workers must be in [1,4]")
    tasks = [(seed, seat) for seed in range(args.seed_start, args.seed_start + args.seeds)
             for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(play, tasks))
    summary = {
        "games": len(rows),
        "pure_wins": sum(row["pure_win"] for row in rows),
        "pure_win_rate_vs_idle": statistics.mean(row["pure_win"] for row in rows),
        "mean_bank": statistics.mean(row["bank"] for row in rows),
        "median_bank": statistics.median(row["bank"] for row in rows),
        "minimum_bank": min(row["bank"] for row in rows),
        "maximum_bank": max(row["bank"] for row in rows),
        "mean_daily_target_realization": statistics.mean(
            row["mean_daily_target_realization"] for row in rows),
        "minimum_daily_target_realization": min(
            row["minimum_daily_target_realization"] for row in rows),
        "minimum_final_observed_day_target_realization": min(
            row["final_observed_day_target_realization"] for row in rows),
        "mean_absolute_productive_assets": statistics.mean(
            row["mean_absolute_productive_assets"] for row in rows),
        "minimum_final_absolute_productive_assets": min(
            row["final_absolute_productive_assets"] for row in rows),
        "maximum_absolute_productive_assets": max(
            row["maximum_absolute_productive_assets"] for row in rows),
        "router_expert_counts": dict(__import__("collections").Counter(
            row["router_expert"] for row in rows)),
        "schema_errors": sum(row["schema_errors"] for row in rows),
        "all_719_calls": all(row["calls"] == 719 for row in rows),
        "mean_latency_us": statistics.mean(row["mean_latency_us"] for row in rows),
        "replacement_claims_created": sum(
            int(row["action_audit"].get("replacement_claim_created", 0)) for row in rows),
        "games_with_replacement_claims": sum(
            int(row["action_audit"].get("replacement_claim_created", 0)) > 0 for row in rows),
        "maximum_live_replacement_claims_observed": max(
            int(row["action_audit"].get("replacement_max_live_observed", 0)) for row in rows),
        "maximum_new_replacement_claims_in_day_observed": max(
            int(row["action_audit"].get("replacement_max_new_in_day_observed", 0)) for row in rows),
        "terminal_replacement_claims_created": sum(
            int(row["action_audit"].get("replacement_terminal_claim_created", 0)) for row in rows),
        "terminal_low_asset_harvests_blocked": sum(
            int(row["action_audit"].get("replacement_terminal_harvest_blocked", 0)) for row in rows),
    }
    audit = originality_audit()
    probe = mechanism_probe()
    scope_violations: list[dict[str, Any]] = []
    for row in rows:
        actual = {
            key.removeprefix("replacement_claim_crop_").upper()
            for key, value in row["action_audit"].items()
            if key.startswith("replacement_claim_crop_") and int(value) > 0
        }
        first_shop = row["first_visible_shops"][0] if row["first_visible_shops"] else None
        allowed = (set(policy.SHOP_PRODUCTS.get(str(first_shop), ())) & set(policy.NON_ONGOING)
                   if row["router_expert"] == "balanced_root" else set())
        if not actual <= allowed:
            scope_violations.append({"seed": row["seed"], "seat": row["seat"],
                                     "actual": sorted(actual), "allowed": sorted(allowed)})
    runtime_contract_pass = (
        summary["maximum_live_replacement_claims_observed"] <= 2
        and summary["maximum_new_replacement_claims_in_day_observed"] <= 2
        and not scope_violations
    )
    passed = (summary["mean_bank"] >= 70_000
              and summary["mean_daily_target_realization"] >= .90
              and summary["minimum_final_absolute_productive_assets"] >= 58
              and summary["schema_errors"] == 0 and summary["all_719_calls"]
              and audit["pass"] and probe["pass"] and runtime_contract_pass)
    payload = {
        "schema": "v116-shop-router-rc6-regression-v1",
        "engine": getattr(KAGSIM, "ENGINE_VERSION", "1.32.7"),
        "contract": {"seeds": [args.seed_start, args.seed_start + args.seeds - 1],
                     "both_seats": True, "workers": args.workers,
                     "mean_bank_gate": 70_000, "mean_target_realization_gate": .90,
                     "minimum_final_productive_assets_gate": 58,
                     "no_target_shrink": "all four final crop targets >=59"},
        "originality_audit": audit,
        "mechanism_probe": probe,
        "runtime_contract": {"scope_violations": scope_violations,
                             "pass": runtime_contract_pass},
        "summary": summary,
        "episodes": rows,
        "decision": ("PASS_RC6_REGRESSION_GATE" if passed else
                     "FAILED_RC6_REGRESSION_GATE_STOP"),
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"summary": summary, "originality": audit, "mechanism_probe": probe,
                      "runtime_contract": payload["runtime_contract"],
                      "decision": payload["decision"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
