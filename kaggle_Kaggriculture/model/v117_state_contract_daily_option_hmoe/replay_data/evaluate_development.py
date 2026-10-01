#!/usr/bin/env python3
"""在已提取的 Replay-derived Development 场景上评测当前 Balanced-only V117。

本脚本只读取白名单场景，不读取原始 Replay；候选与冻结 V1 从 step 0 独立决策，
每个场景交换两次座位。Blind/Confirmation 会被 fail-closed 拒绝。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import math
import os
import random
import statistics
import sys
import sysconfig
from collections import Counter
from pathlib import Path
from typing import Any, Callable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MODEL = ROOT.parent
DEFAULT_PANEL = HERE / "panels/r2_1_v1"
V1_PATH = MODEL / "v1_adaptive_market/main.py"
SCENARIO_BUILD = (MODEL / "v116_heuristic_gold_search" / "replay_arena" / "build")
SOURCES = ("ACCOUNT_ONLINE", "OFFICIAL_DAILY")
RUNTIME_TOP_FILES = ("main.py", "schema.py", "contracts.py", "state_ledger.py")
RUNTIME_DIRS = ("diagnostics", "executor", "experts", "market", "router", "safety")
_SCENARIO_MODULE: Any | None = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def runtime_sha256() -> str:
    paths = [ROOT / name for name in RUNTIME_TOP_FILES]
    for directory in RUNTIME_DIRS:
        paths.extend(sorted((ROOT / directory).glob("*.py")))
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative = path.relative_to(ROOT).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def load_python(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法载入 {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_scenario_engine() -> Any:
    global _SCENARIO_MODULE
    if _SCENARIO_MODULE is not None:
        return _SCENARIO_MODULE
    extension = SCENARIO_BUILD / f"kagsim_scenario{sysconfig.get_config_var('EXT_SUFFIX') or '.so'}"
    if not extension.is_file():
        raise RuntimeError("缺少当前 Python ABI 的 kagsim_scenario；先运行 replay_arena/build_scenario.py")
    _SCENARIO_MODULE = load_python(extension, "kagsim_scenario")
    if str(getattr(_SCENARIO_MODULE, "ENGINE_VERSION", "")) != "1.32.7":
        raise RuntimeError(f"场景引擎版本不一致: {getattr(_SCENARIO_MODULE, 'ENGINE_VERSION', None)!r}")
    return _SCENARIO_MODULE


def validate_action(action: Any, observation: dict[str, Any]) -> int:
    if not isinstance(action, dict) or set(action) != {"farmer", "hands", "market"}:
        return 1
    seat = int(observation.get("player", 0) or 0)
    expected_hands = len((observation.get("farms") or [{}, {}])[seat].get("hands", []) or [])
    return int(
        not isinstance(action.get("farmer"), list)
        or not isinstance(action.get("hands"), list)
        or len(action.get("hands") or []) != expected_hands
        or not isinstance(action.get("market"), list)
        or len(action.get("market") or []) > 10
    )


def visible_shops(schedule: list[dict[str, Any]], step: int) -> list[str]:
    return [str(row["shop"]) for row in schedule if int(row["visible_from_step"]) <= step]


def economy_snapshot(observation: dict[str, Any], seat: int) -> dict[str, Any]:
    farm = (observation.get("farms") or [{}, {}])[seat]
    private = dict(observation.get("private") or {})
    crops: Counter[str] = Counter()
    animals: Counter[str] = Counter()
    structures: Counter[str] = Counter()
    for row in farm.get("tiles", []) or []:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            kind = str(tile.get("kind") or "")
            if kind == "PLANT" and tile.get("crop"):
                crops[str(tile["crop"])] += 1
            if kind in {"PASTURE", "COOP"}:
                structures[kind] += 1
            raw_animal = tile.get("animal")
            animal = raw_animal.get("kind") if isinstance(raw_animal, dict) else raw_animal
            if animal:
                animals[str(animal)] += 1
    carried: Counter[str] = Counter()
    for inventory in private.get("inventories", []) or []:
        carried.update({str(key): max(0, int(value)) for key, value in dict(inventory or {}).items()})
    return {
        "money": int(farm.get("money", 0) or 0),
        "lands": len(farm.get("unlocked_quadrants", []) or []),
        "actors": 1 + len(farm.get("hands", []) or []),
        "crops": dict(crops),
        "animals": dict(animals),
        "structures": dict(structures),
        "shed": {str(key): int(value) for key, value in dict(private.get("shed") or {}).items()},
        "carried": dict(carried),
        "seeds": {str(key): int(value) for key, value in dict(private.get("seeds") or {}).items()},
    }


def load_agents(identity: str, balanced_genome: dict[str, Any], executor_tuning: dict[str, Any]) \
        -> tuple[Any, Callable[[dict[str, Any]], dict[str, Any]]]:
    # 每局独立载入 V1，隔离其 module-level 路由和修复状态。
    candidate_module = load_python(ROOT / "main.py", f"v117_dev_{identity}")
    v1_module = load_python(V1_PATH, f"v1_frozen_{identity}")
    policy = candidate_module.V117Policy(
        balanced_genome=balanced_genome,
        executor_tuning=executor_tuning,
    )
    return policy, v1_module.agent


def play(task: tuple[str, int, dict[str, Any]] | tuple[str, int, dict[str, Any], dict[str, Any]]) \
        -> dict[str, Any]:
    if len(task) == 3:
        scenario_path_raw, candidate_seat, balanced_genome = task
        executor_tuning: dict[str, Any] = {}
    else:
        scenario_path_raw, candidate_seat, balanced_genome, executor_tuning = task
    scenario_path = Path(scenario_path_raw)
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    base = {
        "source_class": scenario.get("source_class"),
        "split": scenario.get("split"),
        "episode_id": scenario.get("episode_id"),
        "observed_date": scenario.get("observed_date"),
        "actual_seed": scenario.get("actual_seed"),
        "scenario_sha256": scenario.get("scenario_sha256"),
        "replay_sha256": scenario.get("replay_sha256"),
        "candidate_seat": int(candidate_seat),
    }
    try:
        if scenario.get("split") != "development":
            raise PermissionError("本评测器只允许 Development")
        if scenario.get("historical_player_fields_materialized") is not False:
            raise RuntimeError("场景包含或未声明排除历史玩家字段")
        if str(scenario.get("module_version")) != "1.32.7":
            raise RuntimeError("场景 module_version 不一致")
        schedule = list(scenario.get("realized_public_shops") or [])
        if not schedule:
            raise RuntimeError("场景缺少商店轨迹")
        if any(int(schedule[index]["visible_from_step"]) < int(schedule[index - 1]["visible_from_step"])
               for index in range(1, len(schedule))):
            raise RuntimeError("商店轨迹时点无序")

        identity = f"{os.getpid()}_{scenario['episode_id']}_{candidate_seat}"
        candidate, v1_agent = load_agents(identity, balanced_genome, executor_tuning)
        agents: list[Callable[[dict[str, Any]], dict[str, Any]]] = [v1_agent, v1_agent]
        agents[candidate_seat] = candidate.act

        engine = load_scenario_engine()
        game = engine.Game(int(scenario["actual_seed"]), int(scenario.get("step_count", 720)))
        game.force_shops(visible_shops(schedule, 0))
        calls = 0
        candidate_action_violations = 0
        trajectory_mismatches = 0
        last_observations: list[dict[str, Any]] = []
        unit_action_counts = [Counter(), Counter()]
        market_order_counts = [Counter(), Counter()]
        market_order_units = [Counter(), Counter()]
        daily_economy: list[dict[str, Any]] = []
        while not game.done:
            step = int(game.step_count)
            observations = [game.observe(0), game.observe(1)]
            last_observations = observations
            if step % 24 == 0:
                daily_economy.append({
                    "day": step // 24,
                    "candidate": economy_snapshot(observations[candidate_seat], candidate_seat),
                    "v1": economy_snapshot(observations[1 - candidate_seat], 1 - candidate_seat),
                })
            expected = visible_shops(schedule, step)
            for observation in observations:
                actual = list((observation.get("town") or {}).get("unlocked_shops") or [])
                trajectory_mismatches += int(actual != expected)
            actions = [agents[index](observations[index]) for index in (0, 1)]
            for player, action in enumerate(actions):
                unit_actions = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
                unit_action_counts[player].update(
                    str(unit_action[0]) if unit_action else "INVALID" for unit_action in unit_actions
                )
                for order in action.get("market", []) or []:
                    if not order:
                        continue
                    op = str(order[0])
                    item = str(order[1]) if len(order) >= 2 else "NONE"
                    quantity = int(order[2]) if len(order) >= 3 else 1
                    market_order_counts[player][f"{op}:{item}"] += 1
                    market_order_units[player][f"{op}:{item}"] += quantity
            candidate_action_violations += validate_action(
                actions[candidate_seat], observations[candidate_seat],
            )
            game.step(actions[0], actions[1])
            if not game.done:
                game.force_shops(visible_shops(schedule, int(game.step_count)))
            calls += 1

        rewards = [float(game.reward(0)), float(game.reward(1))]
        margin = rewards[candidate_seat] - rewards[1 - candidate_seat]
        status = candidate.status()
        seat_status = status["seats"][candidate_seat]
        daily_outcomes = list((seat_status.get("ledger") or {}).get("daily_outcomes") or [])
        router = status["router"]
        router_trace = list((router.get("seats") or {}).get(candidate_seat, {}).get("trace") or [])
        selected = Counter(str(row.get("expert_id")) for row in router_trace)
        return {
            **base,
            "status": "DONE",
            "error": None,
            "calls": calls,
            "candidate_reward": rewards[candidate_seat],
            "v1_reward": rewards[1 - candidate_seat],
            "margin": margin,
            "pure_win": margin > 0,
            "tie": margin == 0,
            "candidate_action_violations": candidate_action_violations,
            "trajectory_mismatches": trajectory_mismatches,
            "router_routable_experts": list(router.get("routable_experts") or []),
            "router_selected_counts": dict(selected),
            "router_switch_count": int((router.get("seats") or {}).get(candidate_seat, {}).get("switch_count", 0)),
            "router_daily_evaluations": len(router_trace),
            "contract_invariant_events": list((seat_status.get("ledger") or {}).get("invariant_events") or []),
            "loss_attribution": dict(seat_status.get("loss_attribution") or {}),
            "candidate_economy": economy_snapshot(last_observations[candidate_seat], candidate_seat),
            "v1_public_economy": economy_snapshot(last_observations[1 - candidate_seat], 1 - candidate_seat),
            "executor_audit": dict(seat_status.get("executor") or {}),
            "market_audit": dict(seat_status.get("market") or {}),
            "candidate_emitted_unit_actions": dict(unit_action_counts[candidate_seat]),
            "v1_emitted_unit_actions": dict(unit_action_counts[1 - candidate_seat]),
            "candidate_emitted_market_orders": dict(market_order_counts[candidate_seat]),
            "candidate_emitted_market_units": dict(market_order_units[candidate_seat]),
            "v1_emitted_market_orders": dict(market_order_counts[1 - candidate_seat]),
            "v1_emitted_market_units": dict(market_order_units[1 - candidate_seat]),
            "daily_economy": daily_economy,
            "daily_totals": {
                "cash_delta": sum(float(row.get("cash_delta", 0)) for row in daily_outcomes),
                "enterprise_value_delta": sum(float(row.get("enterprise_value_delta", 0)) for row in daily_outcomes),
                "productive_actions": sum(int(row.get("productive_actions", 0)) for row in daily_outcomes),
                "moves": sum(int(row.get("moves", 0)) for row in daily_outcomes),
                "idle_actions": sum(int(row.get("idle_actions", 0)) for row in daily_outcomes),
                "overdue_tasks": sum(int(row.get("overdue_tasks", 0)) for row in daily_outcomes),
                "mean_target_realization": (
                    statistics.mean(float(row.get("target_realization_rate", 0)) for row in daily_outcomes)
                    if daily_outcomes else 0.0
                ),
            },
        }
    except Exception as exc:
        return {**base, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def seed_block_ci(rows: list[dict[str, Any]], random_seed: int, draws: int = 5000) -> list[float]:
    blocks: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        blocks.setdefault(int(row["episode_id"]), []).append(row)
    block_values = [statistics.mean(float(row["pure_win"]) for row in block) for block in blocks.values()]
    rng = random.Random(random_seed)
    samples = [statistics.mean(rng.choices(block_values, k=len(block_values))) for _ in range(draws)]
    return [percentile(samples, 0.025), percentile(samples, 0.975)]


def summarize_rows(rows: list[dict[str, Any]], ci_seed: int) -> dict[str, Any]:
    done = [row for row in rows if row.get("status") == "DONE"]
    losses: Counter[str] = Counter()
    for row in done:
        losses.update({
            key: float((value or {}).get("estimated_value", 0.0))
            for key, value in dict((row.get("loss_attribution") or {}).get("totals") or {}).items()
        })
    games = len(done)
    win_rate = statistics.mean(float(row["pure_win"]) for row in done) if done else 0.0
    return {
        "games": games,
        "scenario_blocks": len({row["episode_id"] for row in done}),
        "wins": sum(bool(row["pure_win"]) for row in done),
        "ties": sum(bool(row["tie"]) for row in done),
        "pure_win_rate": win_rate,
        "seed_block_95ci": seed_block_ci(done, ci_seed) if done else [0.0, 0.0],
        "mean_candidate_reward": statistics.mean(float(row["candidate_reward"]) for row in done) if done else 0.0,
        "mean_v1_reward": statistics.mean(float(row["v1_reward"]) for row in done) if done else 0.0,
        "mean_margin": statistics.mean(float(row["margin"]) for row in done) if done else 0.0,
        "median_margin": statistics.median(float(row["margin"]) for row in done) if done else 0.0,
        "catastrophe_rate": statistics.mean(float(row["margin"]) < -10_000 for row in done) if done else 1.0,
        "mean_final_crops": statistics.mean(
            sum(int(value) for value in (row.get("candidate_economy") or {}).get("crops", {}).values())
            for row in done
        ) if done else 0.0,
        "mean_final_animals": statistics.mean(
            sum(int(value) for value in (row.get("candidate_economy") or {}).get("animals", {}).values())
            for row in done
        ) if done else 0.0,
        "mean_productive_actions": statistics.mean(
            int((row.get("daily_totals") or {}).get("productive_actions", 0)) for row in done
        ) if done else 0.0,
        "mean_moves": statistics.mean(
            int((row.get("daily_totals") or {}).get("moves", 0)) for row in done
        ) if done else 0.0,
        "mean_idle_actions": statistics.mean(
            int((row.get("daily_totals") or {}).get("idle_actions", 0)) for row in done
        ) if done else 0.0,
        "error_count": len(rows) - games,
        "action_violations": sum(int(row.get("candidate_action_violations", 0)) for row in done),
        "trajectory_mismatches": sum(int(row.get("trajectory_mismatches", 0)) for row in done),
        "contract_invariant_events": sum(len(row.get("contract_invariant_events") or []) for row in done),
        "mean_loss_proxy_per_game": {
            key: losses[key] / games for key in sorted(losses)
        } if games else {},
        "top_loss_proxies": [
            {"category": key, "mean_proxy_per_game": value / games}
            for key, value in losses.most_common(3)
        ] if games else [],
    }


def manifest_scenarios(panel_dir: Path, limit_per_source: int | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest_path = panel_dir / "replay_panel_manifest_extracted.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected: list[dict[str, Any]] = []
    for source in SOURCES:
        rows = [
            row for row in manifest.get("assignments", [])
            if row.get("source_class") == source and row.get("split") == "development"
        ]
        rows.sort(key=lambda row: (str(row.get("observed_date")), int(row.get("episode_id"))))
        if limit_per_source is not None:
            rows = rows[:limit_per_source]
        selected.extend(rows)
    if any(not row.get("scenario_path") or not row.get("scenario_sha256") for row in selected):
        raise RuntimeError("Development manifest 尚未完成白名单场景提取")
    if any(row.get("split") == "blind_confirmation" and row.get("scenario_path") for row in manifest.get("assignments", [])):
        raise PermissionError("检测到 Blind 场景已被提取；停止 Development 测评")
    return manifest, selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-dir", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--limit-per-source", type=int)
    parser.add_argument("--balanced-genome-json", type=Path)
    parser.add_argument("--executor-tuning-json", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    manifest, scenarios = manifest_scenarios(args.panel_dir, args.limit_per_source)
    balanced_genome = (
        json.loads(args.balanced_genome_json.read_text(encoding="utf-8"))
        if args.balanced_genome_json else {}
    )
    executor_tuning = (
        json.loads(args.executor_tuning_json.read_text(encoding="utf-8"))
        if args.executor_tuning_json else {}
    )
    tasks = [
        (str(row["scenario_path"]), seat, balanced_genome, executor_tuning)
        for row in scenarios for seat in (0, 1)
    ]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))

    source_metrics = {
        source: summarize_rows([row for row in rows if row.get("source_class") == source], 117210 + index)
        for index, source in enumerate(SOURCES)
    }
    overall = summarize_rows(rows, 117219)
    full_panel = args.limit_per_source is None and all(
        source_metrics[source]["scenario_blocks"] == 32 and source_metrics[source]["games"] == 64
        for source in SOURCES
    )
    integrity = (
        overall["error_count"] == 0
        and overall["action_violations"] == 0
        and overall["trajectory_mismatches"] == 0
        and overall["contract_invariant_events"] == 0
        and all(row.get("calls") == 719 for row in rows if row.get("status") == "DONE")
    )
    only_balanced = all(
        row.get("router_routable_experts") == ["BALANCED_BASE"]
        and set(row.get("router_selected_counts") or {}) <= {"BALANCED_BASE"}
        for row in rows if row.get("status") == "DONE"
    )
    payload = {
        "schema": "v117-r2.1-replay-development-balanced-v2",
        "research_version": "V117-R2.1-B",
        "strength_status": "DEVELOPMENT_DIAGNOSTIC_ONLY",
        "candidate_mode": (
            "PARAMETERIZED_BALANCED_ONLY_FALLBACK" if balanced_genome
            else "CURRENT_BALANCED_ONLY_FALLBACK"
        ),
        "balanced_genome": balanced_genome or "R2.1_B_CURRENT_DEFAULT",
        "balanced_genome_sha256": hashlib.sha256(
            json.dumps(balanced_genome, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "executor_tuning": executor_tuning or "R2.1_B_CURRENT_DEFAULT",
        "executor_tuning_sha256": hashlib.sha256(
            json.dumps(executor_tuning, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "opponent": "FROZEN_V1_ADAPTIVE_MARKET",
        "engine": "1.32.7-scenario",
        "candidate_runtime_sha256": runtime_sha256(),
        "v1_sha256": sha256_file(V1_PATH),
        "evaluator_sha256": sha256_file(Path(__file__)),
        "manifest_sha256": sha256_file(args.panel_dir / "replay_panel_manifest_extracted.json"),
        "configuration_sha256": manifest.get("expected_configuration_sha256"),
        "split": "development",
        "source_reporting_order": list(SOURCES),
        "source_metrics": source_metrics,
        "stratified_equal_count_overall": overall,
        "checks": {
            "full_preregistered_panel": full_panel,
            "two_seats_per_scenario": len(tasks) == 2 * len(scenarios),
            "zero_errors_action_trajectory_contract_violations": integrity,
            "historical_actions_market_rewards_not_loaded": True,
            "blind_content_accessed": False,
            "account_and_official_reported_separately": set(source_metrics) == set(SOURCES),
            "current_model_is_balanced_only": only_balanced,
            "hmoe_true_trigger_exit_gate": False,
            "balanced_point_estimate_at_least_20pct": full_panel and integrity and overall["pure_win_rate"] >= 0.20,
            "combined_hmoe_at_least_50pct": False,
        },
        "decision": (
            "R2.1_BALANCED_DEVELOPMENT_DIAGNOSTIC_READY"
            if full_panel and integrity else "EVALUATION_INCOMPLETE_OR_INVALID"
        ),
        "limitations": [
            "这是 Development 诊断，不是冻结 Confirmation，也不是金牌证据",
            "当前默认模型只有 BALANCED_BASE 可路由，不能证明 HMoE 真实触发",
            "当前不是关闭 Router 的正式 Fixed Expert 模式；仅因 registry 中唯一可路由专家为 Balanced 而行为等价",
            "两类来源分别报告；来源差异只触发分布归因，不新增金牌 AND 阈值",
        ],
        "rows": sorted(rows, key=lambda row: (
            str(row.get("source_class")), int(row.get("episode_id") or -1), int(row.get("candidate_seat") or 0)
        )),
    }
    output_dir = args.output_dir or (args.panel_dir / "evaluations/r2_1_a_balanced_vs_v1")
    output_dir.mkdir(parents=True, exist_ok=True)
    games_path = output_dir / "games.jsonl"
    with games_path.open("w", encoding="utf-8") as stream:
        for row in payload.pop("rows"):
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    payload["games_sha256"] = sha256_file(games_path)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if full_panel and integrity else 1


if __name__ == "__main__":
    raise SystemExit(main())
