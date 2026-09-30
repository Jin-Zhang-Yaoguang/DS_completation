#!/usr/bin/env python3
"""V117 R1 全节点、合同、门控、信息边界与运行不变量测试。"""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
import sys
import sysconfig
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = (MODEL / "community_research" / "2026-08-26" / "live_cli" /
          "external_repos" / "kaggriculture-cppsim")
RESULTS = HERE / "framework_test_results.json"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def load_policy() -> Any:
    spec = importlib.util.spec_from_file_location("v117_framework_policy", HERE / "main.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load main.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_engine() -> Any:
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    for build in reversed(builds):
        extension = build / f"kagsim{suffix}"
        if extension.is_file():
            sys.path.insert(0, str(build))
            import kagsim  # type: ignore
            return kagsim
    scenario = (MODEL / "v116_heuristic_gold_search/replay_arena/build" /
                f"kagsim_scenario{suffix}")
    spec = importlib.util.spec_from_file_location("kagsim_scenario", scenario)
    if spec is None or spec.loader is None:
        raise RuntimeError("缺少当前 Python ABI 的 kagsim/kagsim_scenario")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runtime_sources() -> list[Path]:
    roots = [HERE / "main.py", HERE / "schema.py", HERE / "contracts.py", HERE / "state_ledger.py"]
    for folder in ("experts", "router", "executor", "market", "safety", "diagnostics"):
        roots.extend(sorted((HERE / folder).glob("*.py")))
    return roots


def static_audit(paths: list[Path]) -> dict[str, Any]:
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    trees = [ast.parse(path.read_text(encoding="utf-8")) for path in paths]
    agent_defs = [node for tree in trees for node in ast.walk(tree)
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "agent"]
    forbidden = [token for token in (
        "_ACTIONS", "reference_actions", "parent_agent", "load_parent", "v76.agent", "teacher_id",
    ) if token in source]
    long_literals = [len(node.elts) for tree in trees for node in ast.walk(tree)
                     if isinstance(node, (ast.List, ast.Tuple))]
    return {
        "runtime_files": [str(path.relative_to(HERE)) for path in paths],
        "agent_definition_count": len(agent_defs), "forbidden_tokens": forbidden,
        "largest_list_or_tuple_literal": max(long_literals, default=0),
        "embedded_719_stream": any(length >= 700 for length in long_literals),
        "pass": len(agent_defs) == 1 and not forbidden and not any(length >= 700 for length in long_literals),
    }


def main() -> int:
    policy_module = load_policy()
    from contracts import contract_violations
    from diagnostics import build_feedback_report, oracle_readiness, primary_failure

    kagsim = load_engine()
    game = kagsim.Game(117000)
    initial = game.observe(0)
    policy = policy_module.V117Policy()
    state, feedback = policy.ledger.observe(copy.deepcopy(initial))
    contract, switched = policy.router.select(state, feedback)
    policy.ledger.activate_contract(0, contract, switched)
    state_fingerprint = (state.money, state.grid, state.inventories, state.shed, state.seeds)
    after_activation = (state.money, state.grid, state.inventories, state.shed, state.seeds)

    cached_state = replace(state, step=1, hour=1, new_shops=())
    cached, cached_switched = policy.router.select(cached_state, feedback)
    next_day_state = replace(state, step=24, day=1, hour=0, new_shops=())
    next_day, next_day_switched = policy.router.select(next_day_state, feedback)

    # I4 购买依赖图必须能被独立消融，并且土地前置时不得并发放行动物/种子资本。
    from market import MarketController
    tranche_policy = policy_module.V117Policy(balanced_genome={"capital_tranches_enabled": True})
    tranche_state, tranche_feedback = tranche_policy.ledger.observe(copy.deepcopy(initial))
    tranche_contract, _ = tranche_policy.router.select(tranche_state, tranche_feedback)
    tranche_rows, tranche_stage = MarketController._purchase_candidates(
        tranche_state, tranche_contract, tranche_state.shed, Counter(), {},
        tranche_feedback, Counter(), 0,
    )
    tranche_capital_ops = {
        row[1][0] for row in tranche_rows if row[1][0] in {"BUY_LAND", "BUY_ANIMAL", "BUY_SEED"}
    }
    land_contract = replace(
        tranche_contract,
        asset_targets={**dict(tranche_contract.asset_targets), "lands": 2},
    )
    land_rows, land_stage = MarketController._purchase_candidates(
        tranche_state, land_contract, tranche_state.shed, Counter(), {},
        tranche_feedback, Counter(), 0,
    )
    land_capital_ops = {
        row[1][0] for row in land_rows if row[1][0] in {"BUY_LAND", "BUY_ANIMAL", "BUY_SEED"}
    }
    impact_state = replace(
        tranche_state, day=12, step=289, hour=1, money=10000,
        shed={**tranche_state.shed, "MELON": 12, "STRAWBERRY": 12},
        shed_used=24,
        market_inventory={
            **tranche_state.market_inventory,
            "MELON": 10050, "STRAWBERRY": 10050,
        },
    )
    impact_contract = replace(
        tranche_contract,
        purchase_budget=0,
        cash_reserve=0,
        risk_budget={
            **dict(tranche_contract.risk_budget),
            "market_demand_sell_timing_mode": 2.0,
            "market_impact_ordering_enabled": 1.0,
        },
    )
    impact_controller = MarketController()
    impact_result = impact_controller.act(
        impact_state, impact_contract, tranche_feedback, [], {},
    )

    # I5b 必须同时改变合同资产准入与公共执行优先级，且默认路径仍保持关闭。
    planner_policy = policy_module.V117Policy(balanced_genome={
        "value_labor_planner_enabled": True,
        "planner_capacity_units_per_actor": 3,
    })
    planner_state, planner_feedback = planner_policy.ledger.observe(copy.deepcopy(initial))
    planner_contract, planner_switched = planner_policy.router.select(planner_state, planner_feedback)
    planner_policy.ledger.activate_contract(0, planner_contract, planner_switched)
    planner_policy.act(copy.deepcopy(initial))
    planner_status = planner_policy.status()

    # I5c-2 必须形成分阶段资产目标、当前库存再投资预算和收据诊断；默认路径保持关闭。
    calendar_policy = policy_module.V117Policy(balanced_genome={
        "cashflow_calendar_enabled": True,
        "calendar_stage_assets_enabled": True,
        "calendar_opening_assets_enabled": False,
        "calendar_asset_admission_enabled": True,
        "calendar_melon_add": 4,
    })
    calendar_state, calendar_feedback = calendar_policy.ledger.observe(copy.deepcopy(initial))
    calendar_contract, _ = calendar_policy.router.select(calendar_state, calendar_feedback)
    structure_policy = policy_module.V117Policy(balanced_genome={
        "structure_admission_enabled": True,
        "opening_structure_slots": 4,
        "structure_spare_slots": 1,
    })
    structure_state = replace(
        calendar_state, day=4, step=96,
        animals={"SHEEP": 4}, structures={"PASTURE": 4},
    )
    structure_contract, _ = structure_policy.router.select(
        structure_state, calendar_feedback,
    )
    melon_ramp_policy = policy_module.V117Policy(balanced_genome={
        "opening_melon_ramp_add": 4,
        "opening_melon_ramp_start_day": 1,
        "opening_melon_ramp_days": 2,
    })
    melon_ramp_contract, _ = melon_ramp_policy.router.select(
        replace(calendar_state, day=1, step=24), calendar_feedback,
    )
    labor_priority_policy = policy_module.V117Policy(balanced_genome={
        "water_priority": 2,
        "harvest_priority": 1,
        "care_priority": 1,
    })
    labor_priority_contract, _ = labor_priority_policy.router.select(
        calendar_state, calendar_feedback,
    )
    capacity_default_policy = policy_module.V117Policy()
    capacity_feedback_policy = policy_module.V117Policy(balanced_genome={
        "capacity_feedback_enabled": True,
        "capacity_feedback_start_day": 0,
        "capacity_feedback_target_floor_percent": 90,
        "capacity_feedback_overdue_trigger": 4,
        "capacity_feedback_hands_add": 1,
        "capacity_feedback_hands_cap": 12,
    })
    capacity_state = replace(calendar_state, day=2, step=48, hour=0)
    capacity_feedback = replace(
        calendar_feedback,
        previous_day_target_realization=0.50,
        previous_day_overdue_tasks=10,
        capacity_miss_streak=2,
    )
    capacity_default_contract, _ = capacity_default_policy.router.select(
        capacity_state, capacity_feedback,
    )
    capacity_feedback_contract, _ = capacity_feedback_policy.router.select(
        capacity_state, capacity_feedback,
    )
    from executor.common import CommonExecutor, ExecutorTuning, Task
    delivery_probe = CommonExecutor(ExecutorTuning(
        delivery_value_threshold=300,
        delivery_runner_cap=3,
        delivery_cutoff_hour=23,
    ))
    delivery_state = replace(
        calendar_state,
        day=10, step=248, hour=8, money=100,
        positions=((4, 4), (5, 4), (4, 5)),
        inventories=({"MELON": 6}, {"MELON": 6}, {"MELON": 6}),
        shed_used=0,
    )
    delivery_actions = delivery_probe.inventory_actions(
        delivery_state, contract, [],
    )

    # I5d：动物同格会话只锁定已到达的动物格，并按 喂食->收获->收肥->照料 连续执行。
    from schema import animal_kind, quadrant
    service_grid = [list(row) for row in state.grid]
    service_position = CommonExecutor._open_positions(service_grid)[0]
    service_grid[service_position[1]][service_position[0]] = {
        "kind": "PASTURE", "animal": {"kind": "SHEEP"},
    }
    service_executor = CommonExecutor(ExecutorTuning(
        animal_service_session_enabled=True,
        animal_service_max_steps=4,
    ))
    service_chain = f"q{quadrant(service_position)}:{service_position[0]}:{service_position[1]}"
    service_executor.sticky_chain[0] = service_chain
    service_state = replace(
        state,
        grid=tuple(tuple(row) for row in service_grid),
        positions=(service_position,),
        inventories=({"WHEAT": 1},),
    )
    cow_grid = [list(row) for row in service_grid]
    cow_grid[service_position[1]][service_position[0]] = {
        "kind": "PASTURE", "animal": {"kind": "COW"},
        "fed_today": True, "cared_today": False, "yield_units": 0,
        "fertilizer_available": False,
    }
    cow_care_executor = CommonExecutor(ExecutorTuning(
        cow_care_deadline_enabled=True,
        cow_care_deadline_hour=20,
        cow_care_deadline_priority=1,
    ))
    cow_care_tasks = cow_care_executor.tasks(
        replace(
            service_state, day=10, step=260, hour=20,
            grid=tuple(tuple(row) for row in cow_grid),
        ),
        contract, feedback,
    )
    cow_care_due = [task for task in cow_care_tasks if task.action[0] == "CARE"]
    fertilizer_deadline_executor = CommonExecutor(ExecutorTuning(
        fertilizer_collection_deadline_enabled=True,
        fertilizer_collection_deadline_hour=22,
        fertilizer_collection_deadline_priority=1,
    ))
    fertilizer_grid = [list(row) for row in service_grid]
    fertilizer_grid[service_position[1]][service_position[0]] = {
        "kind": "PASTURE", "animal": {"kind": "SHEEP"},
        "fed_today": True, "cared_today": True, "yield_units": 0,
        "fertilizer_available": True,
    }
    fertilizer_deadline_tasks = fertilizer_deadline_executor.tasks(
        replace(
            service_state, day=10, step=262, hour=22,
            grid=tuple(tuple(row) for row in fertilizer_grid),
        ),
        contract, feedback,
    )
    fertilizer_collection_due = [
        task for task in fertilizer_deadline_tasks
        if task.action[0] == "COLLECT_FERTILIZER"
    ]
    fertilizer_priority_grid = [list(row) for row in state.grid]
    fertilizer_priority_positions = CommonExecutor._open_positions(fertilizer_priority_grid)[:2]
    for position, crop in zip(fertilizer_priority_positions, ("MELON", "STRAWBERRY")):
        fertilizer_priority_grid[position[1]][position[0]] = {
            "kind": "PLANT", "crop": crop, "planted_day": 0,
            "watered_today": False, "yield_units": 0,
            "fertilized_until_day": -1,
        }
    strawberry_first_executor = CommonExecutor(ExecutorTuning(
        fertilize_daily_cap=1,
        strawberry_fertilizer_first_enabled=True,
        strawberry_fertilizer_first_start_day=10,
    ))
    strawberry_first_tasks = strawberry_first_executor.tasks(
        replace(
            state, day=10, step=240, hour=0,
            grid=tuple(tuple(row) for row in fertilizer_priority_grid),
            positions=(service_position,), inventories=({"FERTILIZER": 1},),
        ),
        contract, feedback,
    )
    strawberry_first_fertilize = [
        task for task in strawberry_first_tasks if task.action[0] == "FERTILIZE"
    ]
    service_tasks = [
        service_executor._task(contract, priority, *service_position, (verb,), service_chain, 1.0)
        for priority, verb in ((3, "CARE"), (2, "COLLECT_FERTILIZER"),
                               (1, "HARVEST"), (0, "FEED"))
    ]
    service_assignment = service_executor.assign(
        service_state, contract, service_tasks, set(),
    )
    inflight_positions = CommonExecutor._open_positions(service_grid)
    inflight_start, inflight_target = inflight_positions[0], inflight_positions[-1]
    inflight_executor = CommonExecutor(ExecutorTuning(
        inflight_task_lock_enabled=True,
        inflight_task_preempt_priority=0,
    ))
    inflight_task = Task(
        2, inflight_target[0], inflight_target[1], ("WATER",), 22,
        (quadrant(inflight_target), "WATER", None),
        f"q{quadrant(inflight_target)}:{inflight_target[0]}:{inflight_target[1]}",
    )
    inflight_alternative = Task(
        1, inflight_start[0], inflight_start[1], ("CARE",), 24,
        (quadrant(inflight_start), "CARE", None),
        f"q{quadrant(inflight_start)}:{inflight_start[0]}:{inflight_start[1]}",
    )
    inflight_executor.sticky_task[0] = (
        inflight_task.x, inflight_task.y, inflight_task.action,
    )
    inflight_assignment = inflight_executor.assign(
        replace(
            service_state, positions=(inflight_start,), inventories=({},),
        ),
        contract, [inflight_alternative, inflight_task], set(),
    )
    work_conserving_executor = CommonExecutor(ExecutorTuning(
        work_conserving_second_pass_enabled=True,
        work_conserving_max_priority=3,
        work_conserving_max_distance=0,
    ))
    blocked_feed_tasks = [
        Task(
            0, service_position[0], service_position[1], ("FEED",), 20,
            (0, "FEED", index), f"blocked-feed-{index}",
        )
        for index in range(64)
    ]
    fallback_care_task = Task(
        3, service_position[0], service_position[1], ("CARE",), 24,
        (0, "CARE", None), "fallback-care",
    )
    work_conserving_assignment = work_conserving_executor.assign(
        replace(service_state, inventories=({},)),
        contract, [*blocked_feed_tasks, fallback_care_task], set(),
    )
    stable_owner_executor = CommonExecutor(ExecutorTuning(
        stable_tile_owner_enabled=True,
        stable_tile_owner_penalty=50,
    ))
    stable_owner_state = replace(
        service_state,
        positions=(service_position, service_position),
        inventories=({}, {}),
    )
    stable_owner_contract = replace(
        contract,
        asset_targets={**dict(contract.asset_targets), "lands": 1},
    )
    stable_owner_task = Task(
        2, 0, 0, ("WATER",), 22,
        (0, "WATER", None), "stable-owner-far-corner",
    )
    stable_owner = stable_owner_executor._stable_tile_owner(
        stable_owner_task, stable_owner_state, stable_owner_contract,
    )
    stable_owner_cost = stable_owner_executor._task_cost(
        1, service_position, {}, stable_owner_task,
        stable_owner_state, stable_owner_contract,
    )
    stable_non_owner_cost = stable_owner_executor._task_cost(
        0, service_position, {}, stable_owner_task,
        stable_owner_state, stable_owner_contract,
    )
    slack_executor = CommonExecutor(ExecutorTuning(deadline_slack_weight=2.0))
    slack_early_task = Task(
        0, service_position[0], service_position[1], ("WATER",), 20,
        (0, "WATER", "early"), "slack-early",
    )
    slack_late_task = Task(
        0, service_position[0], service_position[1], ("WATER",), 22,
        (0, "WATER", "late"), "slack-late",
    )
    slack_early_cost = slack_executor._task_cost(
        0, service_position, {}, slack_early_task,
        service_state, contract,
    )
    slack_late_cost = slack_executor._task_cost(
        0, service_position, {}, slack_late_task,
        service_state, contract,
    )
    retirement_grid = [list(row) for row in state.grid]
    retirement_positions = CommonExecutor._open_positions(retirement_grid)[:2]
    for position in retirement_positions:
        retirement_grid[position[1]][position[0]] = {
            "kind": "PLANT", "crop": "STRAWBERRY", "planted_day": 0,
            "yield_units": 0, "watered_today": False,
        }
    retirement_executor = CommonExecutor(ExecutorTuning(
        surplus_crop_retirement_enabled=True,
        surplus_crop_retirement_start_day=12,
    ))
    retirement_state = replace(
        state, day=12, step=288, hour=0,
        grid=tuple(tuple(row) for row in retirement_grid),
    )
    retirement_contract = replace(
        contract,
        asset_targets={
            **dict(contract.asset_targets),
            "crops": {"STRAWBERRY": 1},
        },
    )
    retirement_tasks = retirement_executor.tasks(
        retirement_state, retirement_contract, feedback,
    )
    coverage_tasks = [
        Task(0, index, quadrant_id, ("WATER",), 22,
             (quadrant_id, "WATER", None), f"q{quadrant_id}:{index}:{quadrant_id}")
        for quadrant_id in range(3)
        for index in range(4)
    ]
    coverage_pool = CommonExecutor._stratified_candidates(coverage_tasks, 6)
    rolling_executor = CommonExecutor(ExecutorTuning(
        rolling_route_enabled=True,
        rolling_route_horizon=2,
        rolling_route_replan_interval=2,
    ))
    rolling_tasks = [
        Task(0, service_position[0], service_position[1], ("FEED",), 20,
             (0, "FEED", None), "feed"),
        Task(1, service_position[0], service_position[1], ("CARE",), 24,
             (0, "CARE", None), "care"),
    ]
    rolling_routes = rolling_executor._build_rolling_routes(
        service_state, contract, rolling_tasks, [0],
    )
    transition_grid = [list(row) for row in service_state.grid]
    transition_grid[service_position[1]][service_position[0]] = {
        "kind": "PASTURE",
        "animal": {"kind": "SHEEP"},
        "yield_units": 2,
        "fertilizer_available": True,
    }
    transition_state = replace(
        service_state,
        grid=tuple(tuple(row) for row in transition_grid),
    )
    transition_executor = CommonExecutor(ExecutorTuning(
        rolling_route_enabled=True,
        transition_aware_route_enabled=True,
        rolling_route_horizon=4,
        rolling_route_replan_interval=1,
    ))
    transition_tasks = [
        Task(priority, service_position[0], service_position[1], (verb,), 24,
             (0, verb, None), "animal-chain")
        for priority, verb in ((0, "FEED"), (1, "HARVEST"),
                               (2, "COLLECT_FERTILIZER"), (3, "CARE"))
    ]
    transition_routes = transition_executor._build_rolling_routes(
        transition_state, contract, transition_tasks, [0],
    )
    projected_inventory = {"WHEAT": 1}
    for task in transition_tasks:
        transition_executor._route_transition(
            projected_inventory, task, transition_state,
        )
    from safety import SafetyRecoveryTerminalController
    terminal_hire_controller = SafetyRecoveryTerminalController(
        terminal_return_buffer=2, terminal_hire_cap=8,
    )
    terminal_hire_state = replace(
        state, day=29, hour=0, remaining_steps=24, money=5000,
        shed={**state.shed, "MILK": 10, "WOOL": 5},
    )
    terminal_hire_contract = replace(
        contract,
        asset_targets={**dict(contract.asset_targets), "hands": 8},
    )
    terminal_hire_orders = terminal_hire_controller._terminal_market(
        terminal_hire_state, terminal_hire_contract, [["PASS"]],
    )
    terminal_route_executor = CommonExecutor(ExecutorTuning(
        terminal_local_route_enabled=True,
    ))
    terminal_route_assignment = terminal_route_executor.assign(
        replace(transition_state, remaining_steps=24), contract,
        [transition_tasks[0]], set(),
    )

    probe = policy_module.V117Policy()
    first = probe.act(copy.deepcopy(initial))
    game.step(first, {})
    for _ in range(29):
        action = probe.act(game.observe(0))
        game.step(action, {})
    probe_status = probe.status()

    repeat = policy_module.V117Policy()
    action_a = repeat.act(copy.deepcopy(initial))
    serial_a = repeat.ledger.by_seat[0].episode_serial
    action_b = repeat.act(copy.deepcopy(initial))
    serial_b = repeat.ledger.by_seat[0].episode_serial

    rich_feedback_policy = policy_module.V117Policy()
    deterministic_state_a, deterministic_feedback_a = rich_feedback_policy.ledger.observe(copy.deepcopy(initial))
    rich_feedback_policy_b = policy_module.V117Policy()
    deterministic_state_b, deterministic_feedback_b = rich_feedback_policy_b.ledger.observe(copy.deepcopy(initial))

    yarn_observation = copy.deepcopy(initial)
    yarn_observation["town"]["unlocked_shops"] = ["YARN_STORE"]
    yarn_observation["step"] = 72
    yarn_observation["day"] = 3
    yarn_observation["hour"] = 0
    yarn_observation["farms"][0]["money"] = 6000
    yarn_probe = policy_module.V117Policy(allow_unqualified_for_tests=True)
    yarn_probe.act(yarn_observation)
    yarn_status = yarn_probe.status()

    terminal_observation = copy.deepcopy(initial)
    terminal_observation["step"] = 718
    terminal_observation["day"] = 29
    terminal_observation["hour"] = 22
    terminal_probe = policy_module.V117Policy()
    terminal_probe.act(terminal_observation)
    terminal_status = terminal_probe.status()

    feedback_report = build_feedback_report(probe_status)
    loss_status = probe_status["seats"][0]["loss_attribution"]

    router_status = probe_status["router"]
    full_fields = {
        "expert_id", "contract_id", "issued_at", "issued_day", "valid_until_day", "min_dwell_days",
        "eligibility", "terminate_if", "asset_targets", "production_quotas", "inventory_reserves",
        "cash_reserve", "purchase_budget", "sell_priority", "sell_cap", "labor_priority", "deadlines",
        "risk_budget", "transition_cost", "target_realization", "risk_tier",
    }
    checks = {
        "engine_1_32_7": str(kagsim.ENGINE_VERSION) == "1.32.7",
        "canonical_state_has_public_opponent": state.opponent.money == int(initial["farms"][1]["money"]),
        "canonical_state_has_market_history_fields": set(state.price_delta) >= {"WHEAT", "WOOL"},
        "runtime_feedback_is_deterministic": deterministic_state_a == deterministic_state_b and deterministic_feedback_a == deterministic_feedback_b,
        "all_three_experts_implemented": router_status["implemented_experts"] == ["BALANCED_BASE", "YARN_WOOL", "SCARCITY_VEGETABLE"],
        "unqualified_specialists_fail_closed": router_status["routable_experts"] == ["BALANCED_BASE"],
        "complete_daily_contract_schema": full_fields <= set(contract.__dataclass_fields__),
        "contract_has_no_violations": not contract_violations(contract),
        "contract_contains_no_forbidden_information": not any(token in repr(contract).lower()
                                                               for token in ("replay_id", "teacher_id", "future_shop", "seed=")),
        "intraday_contract_is_cached": cached.contract_id == contract.contract_id and not cached_switched,
        "next_day_contract_is_reissued": next_day.contract_id != contract.contract_id and not next_day_switched,
        "router_evaluates_once_per_day": probe_status["router"]["audit"].get("daily_evaluation") == 2,
        "contract_activation_preserves_observed_state": state_fingerprint == after_activation,
        "episode_reset_isolated": serial_b == serial_a + 1 and action_a == action_b,
        "joint_action_schema": set(first) == {"farmer", "hands", "market"},
        "thirty_step_semantic_preflight_clean": probe_status["seats"][0]["control_rewrites"] == 0,
        "executor_e2_is_active": probe_status["seats"][0]["executor"].get("hungarian_calls", 0) > 0,
        "market_m0_m2_is_active_and_m3_gated": (
            probe_status["seats"][0]["market"].get("orders", 0) > 0
            and probe.seats[0].market.enable_opponent_conditioning is False
        ),
        "i4_seed_floor_tranche_is_active": (
            tranche_stage == "SEED_FLOOR" and tranche_capital_ops == {"BUY_SEED"}
        ),
        "i4_land_dependency_is_fail_closed": (
            land_stage == "LAND" and land_capital_ops == {"BUY_LAND"}
        ),
        "i5b_value_capacity_contract_is_active": (
            planner_contract.risk_budget.get("value_labor_planner_enabled") == 1.0
            and planner_contract.risk_budget.get("planner_requested_work", 0)
            > planner_contract.risk_budget.get("planner_admitted_work", 0)
            and planner_contract.labor_priority.get("HARVEST") == 0
            and planner_contract.labor_priority.get("WATER") == 3
        ),
        "i5b_value_priority_executor_is_active": (
            planner_status["seats"][0]["executor"].get("value_labor_planner_turns", 0) > 0
        ),
        "i5b_is_default_off": contract.risk_budget.get("value_labor_planner_enabled") == 0.0,
        "i5c2_cashflow_calendar_contract_is_active": (
            calendar_contract.risk_budget.get("cashflow_calendar_enabled") == 1.0
            and calendar_contract.crops.get("MELON") == 12
            and calendar_contract.animals == {"SHEEP": 2, "COW": 2}
            and calendar_contract.cash_reserve == 20
            and calendar_contract.purchase_budget == 2980
            and calendar_contract.risk_budget.get("calendar_upfront_commitment") == 2830.0
            and calendar_contract.risk_budget.get("calendar_minimum_projected_cash") == 68.0
        ),
        "i5c2_b42_default_is_adopted": (
            contract.risk_budget.get("cashflow_calendar_enabled") == 1.0
            and contract.risk_budget.get("calendar_stage_assets_enabled") == 0.0
            and contract.risk_budget.get("calendar_opening_assets_enabled") == 1.0
            and contract.risk_budget.get("calendar_asset_admission_enabled") == 0.0
            and contract.cash_reserve == 20
            and contract.inventory_reserves.get("WHEAT") == 4
        ),
        "i5c3_structure_admission_is_reachable_and_default_off": (
            structure_contract.asset_targets["structures"]["PASTURE"] == 5
            and policy.router.experts["BALANCED_BASE"].genome.structure_admission_enabled is False
        ),
        "i5c4_opening_melon_ramp_is_reachable_and_default_off": (
            melon_ramp_contract.crops.get("MELON") == 10
            and policy.router.experts["BALANCED_BASE"].genome.opening_melon_ramp_add == 0
        ),
        "i5c5_labor_priority_is_reachable_and_default_preserved": (
            labor_priority_contract.labor_priority.get("WATER") == 2
            and labor_priority_contract.labor_priority.get("HARVEST") == 1
            and labor_priority_contract.labor_priority.get("CARE") == 1
            and contract.labor_priority.get("WATER") == 0
            and contract.labor_priority.get("HARVEST") == 2
            and contract.labor_priority.get("CARE") == 3
        ),
        "i5c6_capacity_feedback_closes_next_day_contract_and_is_default_off": (
            capacity_feedback_contract.hands
            == min(12, capacity_default_contract.hands + 1)
            and capacity_feedback_contract.risk_budget.get(
                "capacity_feedback_triggered"
            ) == 1.0
            and policy.router.experts["BALANCED_BASE"].genome.capacity_feedback_enabled
            is False
        ),
        "i5d_animal_service_session_is_reachable": (
            service_assignment.get(0) is not None
            and service_assignment[0].action == ("FEED",)
            and service_executor.audit.get("animal_service_session_assignment", 0) == 1
        ),
        "i5d_animal_service_session_is_default_off": (
            policy.executor_tuning.animal_service_session_enabled is False
        ),
        "i5d2_inflight_task_lock_is_reachable_and_default_off": (
            inflight_assignment.get(0) == inflight_task
            and inflight_executor.audit.get("inflight_task_lock_assignment") == 1
            and policy.executor_tuning.inflight_task_lock_enabled is False
        ),
        "i5d3_surplus_crop_retirement_is_reachable_and_default_off": (
            sum(task.action == ("DIG",) for task in retirement_tasks) == 1
            and retirement_executor.audit.get("surplus_crop_retirement_dig") == 1
            and policy.executor_tuning.surplus_crop_retirement_enabled is False
        ),
        "i5d4_work_conserving_second_pass_is_reachable_and_default_off": (
            work_conserving_assignment.get(0) == fallback_care_task
            and work_conserving_executor.audit.get(
                "work_conserving_second_pass_assignment"
            ) == 1
            and policy.executor_tuning.work_conserving_second_pass_enabled is False
        ),
        "i5d5_stable_tile_owner_is_reachable_and_default_off": (
            stable_owner == 1
            and stable_non_owner_cost - stable_owner_cost == 50
            and policy.executor_tuning.stable_tile_owner_enabled is False
        ),
        "i5d6_deadline_slack_is_reachable_and_default_zero": (
            slack_late_cost - slack_early_cost == 4.0
            and policy.executor_tuning.deadline_slack_weight == 0.0
        ),
        "i5d7_cow_care_deadline_is_reachable_and_adopted": (
            len(cow_care_due) == 1
            and cow_care_due[0].priority == 1
            and cow_care_executor.audit.get("cow_care_deadline_tasks") == 1
            and policy.executor_tuning.cow_care_deadline_enabled is True
            and policy.executor_tuning.cow_care_deadline_hour == 22
            and policy.executor_tuning.cow_care_deadline_priority == 1
        ),
        "i5d8_fertilizer_collection_deadline_is_reachable_and_default_off": (
            len(fertilizer_collection_due) == 1
            and fertilizer_collection_due[0].priority == 1
            and fertilizer_deadline_executor.audit.get(
                "fertilizer_collection_deadline_tasks"
            ) == 1
            and policy.executor_tuning.fertilizer_collection_deadline_enabled is False
        ),
        "i5d9_strawberry_fertilizer_first_is_reachable_and_adopted": (
            len(strawberry_first_fertilize) == 1
            and (strawberry_first_fertilize[0].x, strawberry_first_fertilize[0].y)
            == fertilizer_priority_positions[1]
            and strawberry_first_executor.audit.get(
                "strawberry_fertilizer_first_turns"
            ) == 1
            and policy.executor_tuning.strawberry_fertilizer_first_enabled is True
            and policy.executor_tuning.strawberry_fertilizer_first_start_day == 12
        ),
        "i5e_b56_windowed_cash_delivery_is_adopted": (
            policy.executor_tuning.delivery_value_threshold == 1500
            and policy.executor_tuning.opening_delivery_value_threshold == 0
            and policy.executor_tuning.opening_delivery_start_day == 0
            and policy.executor_tuning.opening_delivery_until_day == 0
            and policy.executor_tuning.delivery_cash_ceiling == 10000
            and policy.executor_tuning.delivery_max_distance == 20
            and policy.executor_tuning.delivery_cutoff_hour == 18
            and policy.executor_tuning.delivery_runner_cap == 2
            and policy.executor_tuning.fertilize_start_day == 0
        ),
        "i5f_parallel_delivery_is_reachable_and_default_two": (
            len(delivery_actions) == 3
            and {tuple(value) for value in delivery_actions.values()} == {("DROP",)}
            and delivery_probe.audit.get("delivery_parallel_assignments") == 3
            and policy.executor_tuning.delivery_runner_cap == 2
        ),
        "e3c_stratified_candidate_pool_covers_all_quadrants": (
            {task.batch_key[0] for task in coverage_pool} == {0, 1, 2}
            and len(coverage_pool) == 6
            and policy.executor_tuning.stratified_candidate_pool_enabled is False
        ),
        "e3d_priority_weight_is_explicit_and_default_preserved": (
            policy.executor_tuning.priority_weight == 100.0
        ),
        "e3_rolling_route_models_inventory_and_is_default_off": (
            len(rolling_routes[0]) == 2
            and rolling_executor.audit.get("rolling_route_plans") == 1
            and policy.executor_tuning.rolling_route_enabled is False
        ),
        "e3_transition_route_models_chain_and_inventory": (
            transition_routes[0] == [task.key for task in transition_tasks]
            and projected_inventory.get("WHEAT", 0) == 0
            and projected_inventory.get("WOOL", 0) == 2
            and projected_inventory.get("FERTILIZER", 0) == 1
            and transition_executor.audit.get("transition_route_plans") == 1
            and policy.executor_tuning.transition_aware_route_enabled is False
        ),
        "e4_terminal_hire_is_adopted": (
            len(terminal_hire_orders) == 10
            and [order[0] for order in terminal_hire_orders[:2]] == ["SELL", "SELL"]
            and sum(order[0] == "HIRE" for order in terminal_hire_orders) == 8
            and policy.executor_tuning.terminal_hire_cap == 8
        ),
        "e4_terminal_local_route_is_reachable_and_default_off": (
            terminal_route_assignment.get(0) == transition_tasks[0]
            and terminal_route_executor.audit.get("terminal_local_route_turns") == 1
            and policy.executor_tuning.terminal_local_route_enabled is False
        ),
        "m2_market_timing_modes_are_total": (
            MarketController._wait_for_demand(0, 0)
            and MarketController._wait_for_demand(0, 1)
            and not MarketController._wait_for_demand(0, 2)
            and not MarketController._wait_for_demand(1, 0)
            and MarketController._wait_for_demand(1, 1)
            and not MarketController._wait_for_demand(2, 0)
            and MarketController._wait_for_demand(3, 0)
            and not MarketController._wait_for_demand(3, 1)
        ),
        "m2_market_timing_default_preserved": (
            contract.risk_budget.get("market_demand_sell_timing_mode") == 0.0
        ),
        "m2b_market_impact_ordering_is_reachable_and_default_off": (
            len(impact_result.orders) >= 2
            and impact_controller.audit.get("market_impact_ordering_turns") == 1
            and impact_result.orders[0][0] == "SELL"
            and impact_result.orders[1][0] == "SELL"
            and MarketController._sell_impact_score(
                impact_state, str(impact_result.orders[0][1]), int(impact_result.orders[0][2])
            ) >= MarketController._sell_impact_score(
                impact_state, str(impact_result.orders[1][1]), int(impact_result.orders[1][2])
            )
            and policy.router.experts["BALANCED_BASE"].genome.market_impact_ordering_enabled is False
        ),
        "safety_recovery_terminal_node_is_active": probe_status["seats"][0]["safety"].get("mode_normal", 0) > 0,
        "terminal_controller_is_reachable": terminal_status["seats"][0]["control_mode"] == "TERMINAL",
        "daily_outcome_feedback_is_emitted": len(probe_status["seats"][0]["ledger"]["daily_outcomes"]) == 1,
        "r2_1_a_loss_ledger_is_connected": (
            loss_status.get("schema") == "v117-r2.1-a-loss-attribution-v1"
            and len(dict(loss_status.get("totals") or {})) == 7
            and loss_status.get("forbidden_as_strategy_input") is True
        ),
        "specialist_contract_path_is_testable": yarn_status["seats"][0]["expert"] == "YARN_WOOL",
        "specialist_test_mode_does_not_change_default_gate": router_status["routable_experts"] == ["BALANCED_BASE"],
        "oracle_fail_closed_before_specialist_gate": oracle_readiness(router_status)["status"] == "BLOCKED_BY_EXPERT_QUALIFICATION",
        "primary_failure_is_lexicographic": primary_failure({"基础专家弱": True, "语义状态失败": True})["code"] == "语义状态失败",
        "five_layer_feedback_is_complete": set(feedback_report) >= {
            "result_layer", "mechanism_layer", "expert_layer", "router_layer", "robustness_layer"
        },
        "loss_attribution_reaches_feedback_report": (
            "loss_attribution" in feedback_report["mechanism_layer"]
            and "top_losses" in feedback_report["mechanism_layer"]
        ),
    }
    audit = static_audit(runtime_sources())
    checks["originality_static_audit"] = audit["pass"]
    payload = {
        "schema": "v117-r2.1-full-architecture-framework-tests-v3",
        "checks": checks, "static_audit": audit,
        "contract": contract.stable_payload(),
        "router": {"implemented_experts": router_status["implemented_experts"],
                   "routable_experts": router_status["routable_experts"],
                   "audit": router_status["audit"]},
        "pass": all(checks.values()),
    }
    RESULTS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
