#!/usr/bin/env python3
"""Exposed-panel 2x2 causal ablation for RC4's two mechanisms."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib
import json
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
SEARCH = HERE.parent
MODEL = SEARCH.parents[0]
CPPSIM = (MODEL / "community_research" / "2026-08-26" / "live_cli" /
          "external_repos" / "kaggriculture-cppsim")
RC3_RESULTS = SEARCH / "shop_router_rc3" / "smoke_results.json"
RC4_RESULTS = SEARCH / "shop_router_rc4" / "regression_results.json"
sys.path.insert(0, str(HERE))


def _load_cppsim() -> Any:
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError("cppsim build missing")
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    return kagsim


KAGSIM = _load_cppsim()
VARIANTS = {
    "staging_only": "staging_only",
    "projection_only": "projection_only",
}


def asset_metrics(module: Any, executor: Any, obs: dict[str, Any], seat: int) -> dict[str, Any]:
    farm = obs["farms"][seat]
    goal = executor.goal(int(obs.get("day", 0) or 0))
    crops, animals, _structures = module._counts(farm["tiles"])
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
    }


def play(task: tuple[str, int, int]) -> dict[str, Any]:
    mode, seed, seat = task
    module = importlib.import_module(VARIANTS[mode])
    game = KAGSIM.Game(seed)
    executor = module.ShopRouterExecutor()
    daily: list[dict[str, Any]] = []
    schema_errors = 0
    while not game.done:
        obs = game.observe(seat)
        farm = obs["farms"][seat]
        if int(obs.get("hour", 0) or 0) == 23:
            daily.append(asset_metrics(module, executor, obs, seat))
        action = executor.act(obs)
        if (set(action) != {"farmer", "hands", "market"}
                or len(action["hands"]) != len(farm.get("hands", []) or [])
                or len(action["market"]) > 10):
            schema_errors += 1
        pair = [{}, {}]
        pair[seat] = action
        game.step(pair[0], pair[1])
    final = asset_metrics(module, executor, game.observe(seat), seat)
    return {
        "mode": mode,
        "seed": seed,
        "seat": seat,
        "bank": float(game.reward(seat)),
        "idle_bank": float(game.reward(1 - seat)),
        "calls": int(executor.audit["calls"]),
        "schema_errors": schema_errors,
        "router_expert": executor.expert,
        "first_visible_shops": list(executor.first_shops),
        "mean_daily_target_realization": statistics.mean(row["realization"] for row in daily),
        "final_observed_day_target_realization": daily[-1]["realization"],
        "final_absolute_productive_assets": final["productive_assets"],
        "maximum_absolute_productive_assets": max(row["productive_assets"] for row in daily),
        "final_crops": final["crops"],
        "final_animals": final["animals"],
        "action_audit": dict(executor.audit),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "games": len(rows),
        "mean_bank": statistics.mean(row["bank"] for row in rows),
        "median_bank": statistics.median(row["bank"] for row in rows),
        "minimum_bank": min(row["bank"] for row in rows),
        "maximum_bank": max(row["bank"] for row in rows),
        "mean_daily_target_realization": statistics.mean(
            row["mean_daily_target_realization"] for row in rows),
        "minimum_final_absolute_productive_assets": min(
            row["final_absolute_productive_assets"] for row in rows),
        "mean_final_absolute_productive_assets": statistics.mean(
            row["final_absolute_productive_assets"] for row in rows),
        "all_719_calls": all(row["calls"] == 719 for row in rows),
        "schema_errors": sum(row["schema_errors"] for row in rows),
    }


def load_reference(path: Path, mode: str) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    rows = []
    for raw in payload["episodes"]:
        row = copy.deepcopy(raw)
        row["mode"] = mode
        rows.append(row)
    return rows


def code_audit(module_name: str) -> dict[str, Any]:
    module = importlib.import_module(module_name)
    path = HERE / f"{module_name}.py"
    source = path.read_text()
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = [name for name in imports if any(marker in name.lower() for marker in
                 ("replay", "executor", "compiler", "v19", "v20", "v21", "v76",
                  "shop_router_rc3", "shop_router_rc4"))]
    rich = KAGSIM.Game(99117).observe(0)
    poor = copy.deepcopy(rich)
    poor["farms"][0]["money"] = 250
    changed = module.ShopRouterExecutor().act(rich) != module.ShopRouterExecutor().act(poor)
    return {
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "enable_staging": bool(module.ENABLE_STAGING),
        "enable_projection": bool(module.ENABLE_PROJECTION),
        "forbidden_imports": forbidden,
        "money_perturbation_changes_action": changed,
        "contains_actions_constant": "_ACTIONS" in source,
        "pass": not forbidden and changed and "_ACTIONS" not in source,
    }


def metric_effect(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [row[key] for row in rows]
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "minimum": min(values),
        "maximum": max(values),
        "positive": sum(value > 0 for value in values),
        "negative": sum(value < 0 for value in values),
        "zero": sum(value == 0 for value in values),
    }


def paired_payload(all_rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    index = {(mode, int(row["seed"]), int(row["seat"])): row
             for mode, rows in all_rows.items() for row in rows}
    pairs: list[dict[str, Any]] = []
    for seed in range(7100, 7104):
        for seat in (0, 1):
            modes = {mode: index[(mode, seed, seat)] for mode in all_rows}
            metrics = {
                mode: {
                    "bank": row["bank"],
                    "realization": row["mean_daily_target_realization"],
                    "final_assets": row["final_absolute_productive_assets"],
                }
                for mode, row in modes.items()
            }
            effects: dict[str, dict[str, float]] = {}
            for metric in ("bank", "realization", "final_assets"):
                none = metrics["none"][metric]
                staging = metrics["staging_only"][metric]
                projection = metrics["projection_only"][metric]
                both = metrics["both"][metric]
                effects[metric] = {
                    "staging_without_projection": staging - none,
                    "projection_without_staging": projection - none,
                    "staging_with_projection": both - projection,
                    "projection_with_staging": both - staging,
                    "interaction": both - staging - projection + none,
                }
            pairs.append({"seed": seed, "seat": seat, "modes": metrics, "effects": effects})

    effect_names = ("staging_without_projection", "projection_without_staging",
                    "staging_with_projection", "projection_with_staging", "interaction")
    summary: dict[str, Any] = {}
    for metric in ("bank", "realization", "final_assets"):
        summary[metric] = {}
        for effect in effect_names:
            rows = [{effect: pair["effects"][metric][effect]} for pair in pairs]
            summary[metric][effect] = metric_effect(rows, effect)
    return {
        "schema": "v116-rc4-two-by-two-paired-v1",
        "panel": {"seeds": [7100, 7101, 7102, 7103], "both_seats": True,
                  "exposed_mechanism_attribution_only": True},
        "mode_definition": {
            "none": {"staging": False, "projection": False, "source": str(RC3_RESULTS)},
            "staging_only": {"staging": True, "projection": False},
            "projection_only": {"staging": False, "projection": True},
            "both": {"staging": True, "projection": True, "source": str(RC4_RESULTS)},
        },
        "summary": summary,
        "pairs": pairs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=HERE / "ablation_results.json")
    parser.add_argument("--paired-output", type=Path, default=HERE / "paired_comparison.json")
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        raise SystemExit("workers must be in [1,4]")
    tasks = [(mode, seed, seat) for mode in VARIANTS for seed in range(7100, 7104)
             for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        new_rows = list(pool.map(play, tasks))
    all_rows = {
        "none": load_reference(RC3_RESULTS, "none"),
        "staging_only": [row for row in new_rows if row["mode"] == "staging_only"],
        "projection_only": [row for row in new_rows if row["mode"] == "projection_only"],
        "both": load_reference(RC4_RESULTS, "both"),
    }
    paired = paired_payload(all_rows)
    args.paired_output.write_text(json.dumps(paired, ensure_ascii=False, indent=2) + "\n")
    audits = {name: code_audit(name) for name in VARIANTS.values()}
    summaries = {mode: summarize(rows) for mode, rows in all_rows.items()}
    payload = {
        "schema": "v116-rc4-two-by-two-ablation-v1",
        "engine": getattr(KAGSIM, "ENGINE_VERSION", "1.32.7"),
        "contract": {"seeds": [7100, 7103], "both_seats": True, "workers": args.workers,
                     "fresh": False, "gold_arena": False},
        "source_evidence": {"none": str(RC3_RESULTS), "both": str(RC4_RESULTS)},
        "code_audit": audits,
        "mode_summary": summaries,
        "new_episodes": new_rows,
        "paired_output": str(args.paired_output),
        "decision": "MECHANISM_ATTRIBUTION_ONLY_NOT_GOLD_EVIDENCE",
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"mode_summary": summaries, "paired_effects": paired["summary"],
                      "code_audit": audits, "decision": payload["decision"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

