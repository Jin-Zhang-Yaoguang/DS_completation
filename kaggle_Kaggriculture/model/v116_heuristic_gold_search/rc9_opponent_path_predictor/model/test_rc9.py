#!/usr/bin/env python3
"""RC9 mechanism, packaging, compile, and one-step checks; no battles."""

from __future__ import annotations

import copy
import importlib.util
import json
import py_compile
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def blank_grid() -> list[list[Any]]:
    return [[None for _ in range(10)] for _ in range(10)]


def fake_obs(module: Any, step: int, shops: list[str], inventory: dict[str, int] | None = None,
             prices: dict[str, int] | None = None) -> dict[str, Any]:
    market_inventory = {item: 10000 for item in module.PRODUCTS}
    market_inventory.update(inventory or {})
    market_prices = {item: module.BASE_PRICE[item] for item in module.PRODUCTS}
    market_prices.update(prices or {})
    farm = {
        "money": 10_000,
        "farmer": [4, 4],
        "hands": [],
        "tiles": blank_grid(),
        "unlocked_quadrants": [],
    }
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player_index": 0,
        "town": {"unlocked_shops": shops},
        "market": {"inventory": market_inventory, "prices": market_prices},
        "farms": [copy.deepcopy(farm), copy.deepcopy(farm)],
        "private": {"seeds": {}, "shed": {}, "inventories": [{}]},
    }


def mechanism_checks(module: Any) -> dict[str, bool]:
    params = copy.deepcopy(module.DEFAULT_PARAMS)
    frozen = {
        "auction": params["auction"] == {
            "harvest_priority": 3, "plant_priority": 2, "place_priority": 3,
            "sticky_bonus": 5, "role_penalty": 3, "replacement": "none",
        },
        "market": params["market"] == {
            "finance_stress": 48, "ordinary_stress": 8, "sale_floor": 0.45,
            "pressure": 88, "liquidation": 708, "regular_cap": 36,
        },
    }
    modes = all(module.build_executor(params, mode).mode == mode for mode in module.RC9_MODES)

    # Exact D_{t-1}: at prior step 4 ICE_CREAM_SHOP consumes one MILK.
    clean = module.build_executor(params, "router_log_only")
    first = fake_obs(module, 4, ["ICE_CREAM_SHOP"], {"MILK": 10000})
    second = fake_obs(module, 5, ["ICE_CREAM_SHOP"], {"MILK": 10003})
    clean._begin_observation(first)
    clean._begin_observation(second)
    exact_residual = clean.latest_rival_flow.get("MILK") == 4.0

    # Prior own SELL contaminates only that product and must not update its EMA.
    contaminated = module.build_executor(params, "router_log_only")
    contaminated._begin_observation(first)
    contaminated._record_own_market_orders([["SELL", "MILK", 2]])
    contaminated._begin_observation(second)
    own_trade_contamination = (
        "MILK" in contaminated.current_contaminated
        and "MILK" not in contaminated.latest_rival_flow
        and not contaminated._market_collision("MILK")
    )

    # A contiguous day transition is retained; only a skipped step resets.
    continuity = module.build_executor(params, "router_log_only")
    continuity._begin_observation(fake_obs(module, 23, ["BAKERY"]))
    continuity._begin_observation(fake_obs(module, 24, ["BAKERY"], {"WHEAT": 9990}))
    no_cross_day_reset = continuity.market_resets == 0 and "WHEAT" in continuity.flow_ema
    continuity._begin_observation(fake_obs(module, 26, ["BAKERY"]))
    skipped_step_reset = continuity.market_resets == 1 and not continuity.flow_ema

    # Shop is latched from the actual observation, never from a seed label.
    ice = module.build_executor(params, "router_log_only")
    ice._begin_observation(fake_obs(module, 72, ["ICE_CREAM_SHOP"]))
    ice._route(fake_obs(module, 72, ["ICE_CREAM_SHOP"]))
    farmers = module.build_executor(params, "router_log_only")
    farmers._begin_observation(fake_obs(module, 72, ["FARMERS_MARKET"]))
    farmers._route(fake_obs(module, 72, ["FARMERS_MARKET"]))
    endogenous_shop = (
        ice.observed_first_shop == "ICE_CREAM_SHOP"
        and farmers.observed_first_shop == "FARMERS_MARKET"
        and ice.expert == "dairy_berry"
        and farmers.expert == "tomato_market"
    )

    # Fixed leaf modes exercise the same depth-2 interface without identities.
    fixed = module.build_executor(params, "fixed_collision")
    fixed._begin_observation(fake_obs(module, 72, ["FARMERS_MARKET"]))
    fixed._refresh_capacities(fake_obs(module, 72, ["FARMERS_MARKET"]))
    fixed._classify_path()
    fixed_leaf = fixed.path_leaf == "collision" and fixed.diagnostics()["router_depth"] == 2

    # A forced scarcity leaf must alter only the future aggregate stage block,
    # keep its size, and leave the common opening untouched.
    target = module.build_executor(params, "fixed_scarcity")
    target_obs = fake_obs(module, 120, ["PET_CAFE"])
    target._begin_observation(target_obs)
    target._refresh_capacities(target_obs)
    target._classify_path()
    target._route(target_obs)
    before_stage = module.daily_goal(target.genomes[target.expert], 5)
    target._maybe_commit_stages(5)
    after_stage = target.goal(5)
    target_overlay = (
        sum(before_stage["crops"].values()) == sum(after_stage["crops"].values())
        and after_stage["crops"].get("CARROT", 0) > before_stage["crops"].get("CARROT", 0)
        and target.goal(0)["crops"] == module.daily_goal(target.genomes[target.expert], 0)["crops"]
    )

    # Strong market policy is allowed on a clean collision but blocked when
    # the sample is contaminated.  Purchase-bearing batches remain untouched.
    policy = module.build_executor(params, "fixed_collision")
    policy.current_step = 100
    policy.collision_product = "MILK"
    policy.current_prices = {item: module.BASE_PRICE[item] for item in module.PRODUCTS}
    policy.current_inventory = {item: 10000 for item in module.PRODUCTS}
    policy.current_inventory["MILK"] = 10024
    policy.flow_ema["MILK"] = 12.0
    policy.last_clean_step["MILK"] = 100
    market_obs = fake_obs(module, 100, ["ICE_CREAM_SHOP"], {"MILK": 10024})
    withheld = policy._apply_market_policy(market_obs, [["SELL", "MILK", 36]]) == []
    policy.current_contaminated = {"MILK"}
    contamination_blocks_trigger = (
        policy._apply_market_policy(market_obs, [["SELL", "MILK", 36]])
        == [["SELL", "MILK", 36]]
    )
    financing_safe = (
        policy._apply_market_policy(
            market_obs, [["SELL", "MILK", 36], ["BUY_SEED", "WHEAT", 1]]
        ) == [["SELL", "MILK", 36], ["BUY_SEED", "WHEAT", 1]]
    )

    json_serializable = bool(json.dumps(fixed.diagnostics(), sort_keys=True))
    return {
        "p0064_auction_frozen": frozen["auction"],
        "p0064_market_frozen": frozen["market"],
        "all_required_modes": modes,
        "prev_step_prev_shop_demand_exact": exact_residual,
        "own_product_trade_contaminates_residual": own_trade_contamination,
        "cross_day_continuity_preserved": no_cross_day_reset,
        "non_contiguous_step_resets": skipped_step_reset,
        "actual_shop_not_seed_label": endogenous_shop,
        "router_depth_two_and_fixed_leaf": fixed_leaf,
        "future_aggregate_target_overlay_only": target_overlay,
        "clean_collision_market_withhold": withheld,
        "contamination_blocks_strong_trigger": contamination_blocks_trigger,
        "same_turn_financing_passthrough": financing_safe,
        "diagnostics_json_serializable": json_serializable,
    }


def engine_one_step(module: Any) -> dict[str, Any]:
    model = HERE.parents[2]
    cppsim = (model / "community_research" / "2026-08-26" / "live_cli" /
              "external_repos" / "kaggriculture-cppsim")
    builds = sorted((cppsim / "build").glob("lib.*"))
    if not builds:
        return {"available": False, "pass": False, "reason": "cppsim build missing"}
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    game = kagsim.Game(99109)
    result: dict[str, Any] = {"available": True, "modes": {}}
    passed = True
    actions: dict[str, Any] = {}
    for mode in module.RC9_MODES:
        executor = module.build_executor(module.DEFAULT_PARAMS, mode)
        obs = game.observe(0)
        action = executor.act(obs)
        actions[mode] = action
        farm = obs["farms"][0]
        valid = (set(action) == {"farmer", "hands", "market"}
                 and len(action["hands"]) == len(farm.get("hands", []) or [])
                 and len(action["market"]) <= 10)
        result["modes"][mode] = {"pass": valid, "diagnostics": executor.diagnostics()}
        passed = passed and valid
    result["base_router_log_action_identical"] = actions["base"] == actions["router_log_only"]
    passed = passed and result["base_router_log_action_identical"]
    result["pass"] = passed
    return result


def main() -> int:
    main_path = HERE / "main.py"
    manifest_path = HERE / "manifest.json"
    if not main_path.exists() or not manifest_path.exists():
        raise SystemExit("run packager.py first")
    py_compile.compile(str(HERE / "overlay.py"), doraise=True)
    py_compile.compile(str(HERE / "packager.py"), doraise=True)
    py_compile.compile(str(main_path), doraise=True)
    module = load_module(main_path, "rc9_test_main")
    checks = mechanism_checks(module)
    engine = engine_one_step(module)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    passed = all(checks.values()) and engine["pass"] and manifest["evaluation"]["games"] == 0
    payload = {
        "schema": "v116-rc9-model-test-v1",
        "py_compile": {"overlay.py": True, "packager.py": True, "main.py": True},
        "mechanism_checks": checks,
        "engine_one_step": engine,
        "battle_evaluation_run": False,
        "pass": passed,
    }
    (HERE / "test_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
