#!/usr/bin/env python3
"""Synthetic-only parity and fixed-shop scenario tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import py_compile
import sysconfig
from collections import Counter
from pathlib import Path
from typing import Any

from scenario_runner import ScenarioRunner, pass_agent


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent.parent
CPPSIM_ROOT = (MODEL_ROOT / "community_research" / "2026-08-26" / "live_cli" /
               "external_repos" / "kaggriculture-cppsim")
RESULTS = HERE / "test_results.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def original_hashes() -> dict[str, str]:
    suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    paths = sorted(path for path in CPPSIM_ROOT.rglob(f"kagsim*{suffix}") if path.is_file())
    return {str(path.relative_to(CPPSIM_ROOT)): sha256(path) for path in paths}


def load_extension(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_modules() -> tuple[Any, Any]:
    suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    originals = sorted((CPPSIM_ROOT / "build").glob(f"lib.*/kagsim*{suffix}"))
    scenarios = sorted((HERE / "build").glob(f"kagsim_scenario*{suffix}"))
    if not originals or len(scenarios) != 1:
        raise RuntimeError("missing original or scenario extension; run build_scenario.py")
    return load_extension("kagsim", originals[-1]), load_extension("kagsim_scenario", scenarios[0])


def empty_schedule_parity(original: Any, scenario: Any) -> dict[str, Any]:
    seed = 24681357
    steps = 720
    reference = original.Game(seed, steps)
    arena = ScenarioRunner(seed, pass_agent, pass_agent, (), steps, module=scenario)
    checked = 0
    while not reference.done:
        ref_a = reference.observe(0)
        ref_b = reference.observe(1)
        arena_a, arena_b = arena.observations()
        if ref_a != arena_a or ref_b != arena_b:
            return {"pass": False, "checked_steps": checked,
                    "reason": f"observation mismatch at step {checked}"}
        reference.step(pass_agent(ref_a), pass_agent(ref_b))
        arena.step_once()
        rewards_equal = (
            float(reference.reward(0)) == float(arena.game.reward(0))
            and float(reference.reward(1)) == float(arena.game.reward(1))
        )
        if not rewards_equal:
            return {"pass": False, "checked_steps": checked,
                    "reason": f"reward mismatch after step {checked}"}
        checked += 1
    final_equal = (
        arena.game.done and arena.step_count == reference.step_count
        and float(reference.reward(0)) == float(arena.game.reward(0))
        and float(reference.reward(1)) == float(arena.game.reward(1))
    )
    return {"pass": final_equal, "checked_steps": checked,
            "rewards": [float(reference.reward(0)), float(reference.reward(1))]}


def fixed_schedule_and_demand(scenario: Any) -> dict[str, Any]:
    schedule = [
        {"shop": "BAKERY", "visible_from_step": 72},
        {"shop": "PET_CAFE", "visible_from_step": 144},
    ]
    arena = ScenarioRunner(97531, pass_agent, pass_agent, schedule, 148, module=scenario)
    visibility: dict[int, list[str]] = {}
    demand_deltas: dict[int, dict[str, int]] = {}
    while not arena.game.done:
        step = arena.step_count
        obs_a, obs_b = arena.observations()
        if step in {71, 72, 143, 144}:
            visibility[step] = list(obs_a["town"]["unlocked_shops"])
        before = dict(obs_a["market"]["inventory"])
        arena.step_once()
        if step in {72, 144}:
            after = dict(arena.game.observe(0)["market"]["inventory"])
            demand_deltas[step] = {
                item: int(after[item]) - int(before[item])
                for item in ("WHEAT", "EGG", "CARROT")
            }
        if obs_a["town"] != obs_b["town"] or obs_a["market"] != obs_b["market"]:
            return {"pass": False, "reason": f"seat public state mismatch at {step}"}
    expected_visibility = {
        71: [], 72: ["BAKERY"], 143: ["BAKERY"],
        144: ["BAKERY", "PET_CAFE"],
    }
    # At both 72 and 144 the daily center removes one of every product.
    # BAKERY additionally removes WHEAT+EGG once; PET_CAFE removes CARROT twice.
    expected_deltas = {
        72: {"WHEAT": -2, "EGG": -2, "CARROT": -1},
        144: {"WHEAT": -2, "EGG": -2, "CARROT": -3},
    }
    return {
        "pass": visibility == expected_visibility and demand_deltas == expected_deltas,
        "visibility": visibility,
        "demand_deltas": demand_deltas,
    }


def direct_force_and_two_seats(scenario: Any) -> dict[str, Any]:
    game = scenario.Game(1234, 5)
    game.force_shops(["ICE_CREAM_SHOP"])
    direct = (
        game.observe(0)["town"]["unlocked_shops"] == ["ICE_CREAM_SHOP"]
        and game.observe(1)["town"]["unlocked_shops"] == ["ICE_CREAM_SHOP"]
    )
    calls: Counter[int] = Counter()
    seen: dict[int, list[int]] = {0: [], 1: []}

    def agent(obs: dict[str, Any]) -> dict[str, Any]:
        seat = int(obs["player"])
        calls[seat] += 1
        seen[seat].append(int(obs["step"]))
        return pass_agent(obs)

    arena = ScenarioRunner(
        4321, agent, agent,
        [{"shop": "FARMERS_MARKET", "visible_from_step": 2}],
        6, module=scenario,
    )
    result = arena.run()
    live_both = calls == Counter({0: 5, 1: 5}) and seen[0] == seen[1] == list(range(5))
    return {"pass": direct and live_both and result.steps == 5,
            "direct_force": direct, "calls": dict(calls), "seen": seen}


def main() -> int:
    before = original_hashes()
    manifest = json.loads((HERE / "build_manifest.json").read_text(encoding="utf-8"))
    original, scenario = load_modules()
    py_compile.compile(str(HERE / "build_scenario.py"), doraise=True)
    py_compile.compile(str(HERE / "scenario_runner.py"), doraise=True)
    py_compile.compile(str(HERE / "test_scenario.py"), doraise=True)
    parity = empty_schedule_parity(original, scenario)
    fixed = fixed_schedule_and_demand(scenario)
    seats = direct_force_and_two_seats(scenario)
    after = original_hashes()
    versions = {
        "original": getattr(original, "ENGINE_VERSION", None),
        "scenario": getattr(scenario, "ENGINE_VERSION", None),
    }
    checks = {
        "py_compile": True,
        "module_version_1_32_7": versions == {"original": "1.32.7", "scenario": "1.32.7"},
        "empty_schedule_stepwise_parity": parity["pass"],
        "fixed_schedule_visibility_and_demand": fixed["pass"],
        "runtime_force_shops_and_two_seats": seats["pass"],
        "original_so_hashes_unchanged": before == after,
        "build_manifest_original_unchanged": manifest["upstream"]["unchanged"],
        "synthetic_only": True,
    }
    payload = {
        "schema": "v116-replay-arena-test-v1",
        "checks": checks,
        "versions": versions,
        "empty_schedule_parity": parity,
        "fixed_schedule": fixed,
        "two_seats": seats,
        "original_shared_objects_before": before,
        "original_shared_objects_after": after,
        "real_replay_read": False,
        "gold_battles_run": 0,
        "pass": all(checks.values()),
    }
    RESULTS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
