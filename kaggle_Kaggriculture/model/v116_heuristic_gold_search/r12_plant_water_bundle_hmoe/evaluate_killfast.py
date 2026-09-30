#!/usr/bin/env python3
"""Single-process, single-seed kill-fast evaluator for R12."""

from __future__ import annotations

from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import traceback
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
MODEL = HERE / "main.py"
IDLE = {"farmer": ["PASS"], "hands": [], "market": []}


def load_candidate():
    spec = importlib.util.spec_from_file_location("r12_killfast_candidate", MODEL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_kagsim():
    cppsim = HERE.parents[1] / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
    candidates = sorted((cppsim / "build").glob("lib*/kagsim*.so"))
    if not candidates:
        raise RuntimeError("validated local kagsim build not found")
    sys.path.insert(0, str(candidates[-1].parent))
    import kagsim  # type: ignore
    return kagsim


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def tile_at(grid: list[list[Any]], position: tuple[int, int]) -> Any:
    x, y = position
    return grid[y][x] if 0 <= y < len(grid) and 0 <= x < len(grid[y]) else None


def animal(tile: Any) -> str | None:
    if not isinstance(tile, Mapping):
        return None
    value = tile.get("animal")
    return str(value.get("kind")) if isinstance(value, Mapping) and value.get("kind") else \
        str(value) if value else None


def snapshot(obs: Mapping[str, Any]) -> dict[str, Any]:
    farm = list(obs.get("farms") or [{}, {}])[0]
    crops: Counter[str] = Counter()
    animals: Counter[str] = Counter()
    weeds = 0
    dry_risk = 0
    for row in farm.get("tiles", []) or []:
        for tile in row or []:
            if not isinstance(tile, Mapping):
                continue
            if tile.get("kind") == "PLANT":
                crops[str(tile.get("crop"))] += 1
                dry_risk += int(not tile.get("watered_today")
                                and int(tile.get("consecutive_unwatered", 0) or 0) >= 1)
            if tile.get("kind") == "WEED":
                weeds += 1
            if animal(tile):
                animals[str(animal(tile))] += 1
    return {
        "step": int(obs.get("step", 0) or 0),
        "day": int(obs.get("day", 0) or 0),
        "hour": int(obs.get("hour", 0) or 0),
        "money": int(farm.get("money", 0) or 0),
        "assets": sum(crops.values()) + sum(animals.values()),
        "crops": dict(sorted(crops.items())),
        "animals": dict(sorted(animals.items())),
        "weeds": weeds,
        "dry_risk": dry_risk,
        "hands": len(farm.get("hands", []) or []),
        "lands": len(farm.get("unlocked_quadrants", []) or []),
    }


def semantic_invalid(action: Mapping[str, Any], obs: Mapping[str, Any]) -> Counter[str]:
    farm = list(obs.get("farms") or [{}, {}])[0]
    grid = list(farm.get("tiles", []) or [])
    positions = [farm.get("farmer")] + list(farm.get("hands", []) or [])
    inventories = list(dict(obs.get("private") or {}).get("inventories", []) or [])
    verbs = [action.get("farmer", ["PASS"])] + list(action.get("hands", []) or [])
    invalid: Counter[str] = Counter()
    for index, verb in enumerate(verbs):
        if index >= len(positions) or not positions[index] or not verb:
            continue
        op = str(verb[0])
        if op not in {"WATER", "FEED", "PLACE"}:
            continue
        position = (int(positions[index][0]), int(positions[index][1]))
        tile = tile_at(grid, position)
        inventory = dict(inventories[index] or {}) if index < len(inventories) else {}
        valid = True
        if op == "WATER":
            valid = isinstance(tile, Mapping) and tile.get("kind") == "PLANT" \
                and not bool(tile.get("watered_today"))
        elif op == "FEED":
            valid = bool(animal(tile)) and not bool(tile.get("fed_today")) \
                and int(inventory.get("WHEAT", 0) or 0) > 0
        elif op == "PLACE":
            item = str(verb[1]) if len(verb) > 1 else ""
            want = "COOP" if item == "GOOSE" else "PASTURE"
            valid = isinstance(tile, Mapping) and tile.get("kind") == want \
                and not animal(tile) and int(inventory.get(item, 0) or 0) > 0
        if not valid:
            invalid[op] += 1
    return invalid


def missed_water_loss(before: Mapping[str, Any], after: Mapping[str, Any]) -> int:
    before_grid = list(list(before.get("farms") or [{}, {}])[0].get("tiles", []) or [])
    after_grid = list(list(after.get("farms") or [{}, {}])[0].get("tiles", []) or [])
    losses = 0
    for y, row in enumerate(before_grid):
        for x, tile in enumerate(row or []):
            if not isinstance(tile, Mapping) or tile.get("kind") != "PLANT":
                continue
            exposed = not bool(tile.get("watered_today")) \
                and int(tile.get("consecutive_unwatered", 0) or 0) >= 1
            next_tile = tile_at(after_grid, (x, y))
            losses += int(exposed and isinstance(next_tile, Mapping)
                          and next_tile.get("kind") == "WEED")
    return losses


def main() -> None:
    module = load_candidate()
    kagsim = load_kagsim()
    game = kagsim.Game(7100, steps=720)
    executor = module.build_executor(params=None, mode="router")
    invalid: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    daily: list[dict[str, Any]] = []
    runtime_errors: list[dict[str, Any]] = []
    missed_water_weeds = 0
    step144: dict[str, Any] | None = None
    previous_obs: Mapping[str, Any] | None = None
    calls = 0
    while not game.done:
        obs = game.observe(0)
        if previous_obs is not None and int(obs.get("day", 0)) != int(previous_obs.get("day", 0)):
            missed_water_weeds += missed_water_loss(previous_obs, obs)
        if int(obs.get("hour", 0) or 0) == 0:
            row = snapshot(obs)
            row["diagnostics"] = executor.diagnostics()
            daily.append(row)
        if int(obs.get("step", 0) or 0) == 144:
            step144 = snapshot(obs)
        try:
            action = executor.act(obs)
            calls += 1
            invalid.update(semantic_invalid(action, obs))
            action_counts.update([str(action["farmer"][0])])
            action_counts.update(str(verb[0]) for verb in action["hands"])
        except Exception as exc:
            runtime_errors.append({"step": int(obs.get("step", 0) or 0),
                                   "error": repr(exc), "traceback": traceback.format_exc()})
            action = {"farmer": ["PASS"],
                      "hands": [["PASS"] for _ in list(obs["farms"][0].get("hands", []) or [])],
                      "market": []}
        game.step(action, IDLE)
        previous_obs = obs
    terminal_obs = game.observe(0)
    terminal = snapshot(terminal_obs)
    diagnostics = executor.diagnostics()
    gates = {
        "calls_719": calls == 719,
        "runtime_errors_zero": not runtime_errors,
        "step144_assets_ge_12": step144 is not None and int(step144["assets"]) >= 12,
        "missed_water_weeds_zero": missed_water_weeds == 0,
        "terminal_bank_ge_60000": float(game.reward(0)) >= 60000,
        "terminal_assets_ge_30": int(terminal["assets"]) >= 30,
        "invalid_water_feed_place_zero": sum(invalid.values()) == 0,
        "orphan_live_zero": int(diagnostics["orphan_live_tickets"]) == 0,
        "expired_live_zero": int(diagnostics["expired_live_tickets"]) == 0,
    }
    result = {
        "schema": "v116-r12-killfast-evidence-v1",
        "candidate_schema": module.SCHEMA,
        "candidate_sha256": sha256(MODEL),
        "engine_version": str(kagsim.ENGINE_VERSION),
        "seed": 7100,
        "opponent": "idle",
        "mode": "router",
        "single_process": True,
        "calls": calls,
        "bank": float(game.reward(0)),
        "step144": step144,
        "terminal": terminal,
        "missed_water_weeds": missed_water_weeds,
        "invalid_actions": dict(sorted(invalid.items())),
        "action_counts": dict(sorted(action_counts.items())),
        "runtime_errors": runtime_errors,
        "diagnostics": diagnostics,
        "gates": gates,
        "passed": all(gates.values()),
        "decision": "KILLFAST_PASS_READY_FOR_PARENT_REVIEW" if all(gates.values())
                    else "NOT_GOLD_KILLFAST_REJECT",
        "scope": "One exposed seed versus idle; never gold evidence.",
    }
    (HERE / "daily_diagnostics.json").write_text(
        json.dumps(daily, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (HERE / "killfast_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
