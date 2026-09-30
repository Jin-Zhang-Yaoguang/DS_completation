#!/usr/bin/env python3
"""重建已存在诊断动作轨迹的 step320，短分叉仅诊断容量选格；不打开 Replay。"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
import gzip
import hashlib
import json

import run_dependency_microcases as d

HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
TRACE = MODEL / "evaluation/r0_pass_s0/trace_1950905001_seat0.json.gz"
OLD = '    reserve = set(ranked[:max(4, animal_total)])'
NEW = '''    # 仅诊断容量选格：活作物不计可建格，已有建筑先占容量。
    structures = {p for p in owned if isinstance(farm["tiles"][p[1]][p[0]], dict)
                  and farm["tiles"][p[1]][p[0]].get("kind") in ("PASTURE", "COOP")}
    buildable = [p for p in ranked if farm["tiles"][p[1]][p[0]] is None
                 or isinstance(farm["tiles"][p[1]][p[0]], dict) and farm["tiles"][p[1]][p[0]].get("kind") == "WEED"]
    reserve = structures | set(buildable[:max(0, max(4, animal_total) - len(structures))])'''


def diagnostic_module():
    source = (HERE / "snapshot/v125_r0_main.py").read_text()
    assert source.count(OLD) == 1
    source = source.replace(OLD, NEW)
    mod = ModuleType("capacity_selection_diagnostic")
    exec(compile(source, "<capacity_selection_diagnostic>", "exec"), mod.__dict__)
    return mod, hashlib.sha256(source.encode()).hexdigest()


def analyze(obs, mod):
    action = mod.agent(obs)
    st = mod._STATES[obs["player"]]
    plan = mod.economic_plan(obs, st)
    tasks = mod.make_tasks(obs, st, plan)
    f = obs["farms"][obs["player"]]
    owned = [(x, y) for y, row in enumerate(f["tiles"]) for x, t in enumerate(row) if t != "LOCKED"]
    ranked = sorted(owned, key=lambda p: (mod.dist(p, mod.home(p)), p[1], p[0]))
    n = max(4, sum(plan["counts"][a] for a in mod.ANIMALS))
    reserve = ranked[:n]
    buildable = [p for p in owned if f["tiles"][p[1]][p[0]] is None or
                 isinstance(f["tiles"][p[1]][p[0]], dict) and f["tiles"][p[1]][p[0]].get("kind") == "WEED"]
    structures = [p for p in owned if isinstance(f["tiles"][p[1]][p[0]], dict)
                  and f["tiles"][p[1]][p[0]].get("kind") in ("PASTURE", "COOP")]
    return {"counts": dict(plan["counts"]), "original_reserve": [{"pos": p, "tile": f["tiles"][p[1]][p[0]]} for p in reserve],
            "structures": structures, "buildable_outside_original_reserve": [p for p in buildable if p not in reserve],
            "in_transit": {a: mod.inventory_total(obs["private"], a) for a in mod.ANIMALS},
            "build_tasks": [t for t in tasks if t["kind"] == "build"], "action": action}


def short_branch(env, module, label):
    # 同一真实 step320 状态，仅替换 reserve 的选择算法，采购/ROI/任务值均不修改。
    local = deepcopy(env)
    rows = []
    for _ in range(12):
        obs = d.engine.observed(local, 0)
        result = analyze(obs, module)
        d.engine.official_step(local, [result["action"], deepcopy(d.engine.PASS)])
        nxt = d.engine.observed(local, 0)
        rows.append({"step": obs["step"], "build_task_count": len(result["build_tasks"]),
                     "action": result["action"], "placed_cows_after": sum(isinstance(t, dict) and t.get("animal") == "COW" for row in nxt["farms"][0]["tiles"] for t in row),
                     "in_transit_after": {a: module.inventory_total(nxt["private"], a) for a in module.ANIMALS}})
    return {"label": label, "rows": rows, "final_observation": d.engine.observed(local, 0)}


def main():
    assert d.engine.sha(d.engine.RULES.__file__) == d.engine.EXPECTED_RULES_SHA
    trace = json.loads(gzip.decompress(TRACE.read_bytes()))
    env = d.engine.make("kaggriculture", configuration={"seed": trace["seed"], "episodeSteps": 720}, debug=False)
    env.reset(2)
    for action in trace["actions"][:320]:
        env.step(action)
    obs = deepcopy(dict(env._Environment__get_shared_state(0).observation))
    baseline = analyze(obs, d.load())
    alternative, alt_sha = diagnostic_module()
    patched = analyze(obs, alternative)
    branches = [short_branch(env, d.load(), "r0"), short_branch(env, diagnostic_module()[0], "capacity_selection_only")]
    checks = {
        "reconstructed_step320": obs["step"] == 320,
        "recomputed_r0_action_matches_trace": baseline["action"] == trace["actions"][320][0],
        "baseline_short_branch_matches_saved_trace": all(row["action"] == trace["actions"][row["step"]][0] for row in branches[0]["rows"]),
        "three_cows_in_transit": baseline["in_transit"]["COW"] == 3,
        "seventeen_assets_fourteen_structures": sum(baseline["counts"].get(a, 0) for a in d.load().ANIMALS) == 17 and len(baseline["structures"]) == 14,
        "three_crops_miscounted_in_reserve": sum(isinstance(p["tile"], dict) and p["tile"].get("kind") == "PLANT" for p in baseline["original_reserve"]) == 3,
        "free_land_but_zero_baseline_build_tasks": len(baseline["buildable_outside_original_reserve"]) == 17 and not baseline["build_tasks"],
        "capacity_selection_produces_three_build_tasks": len(patched["build_tasks"]) == 3,
        "counterfactual_constructs_without_clearing_live_crops": all(t["pos"] in baseline["buildable_outside_original_reserve"] for t in patched["build_tasks"]),
        "short_branch_places_more_cows": branches[1]["rows"][-1]["placed_cows_after"] > branches[0]["rows"][-1]["placed_cows_after"],
    }
    result = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "method": "仅重建已存在本地诊断动作轨迹至step320；同状态12帧容量选格反事实；不是新seed完整比赛、不是确认面板或胜率证据",
              "source_trace": str(TRACE), "source_trace_sha256": d.engine.sha(TRACE),
              "r0_sha256": d.EXPECTED_R0, "capacity_only_source_sha256": alt_sha,
              "diagnostic_replacement": {"old": OLD, "new": NEW},
              "harness_sha256": d.engine.sha(__file__), "engine_sha256": d.engine.sha(d.engine.RULES.__file__),
              "replay_reads": 0, "local_diagnostic_traces_read": 1, "blind_reads": 0, "workers": 1,
              "historical_prefix_transitions": 320, "counterfactual_transitions": 24,
              "baseline": baseline, "capacity_selection_only": patched, "branches": branches,
              "checks": checks, "pass": all(checks.values())}
    (HERE / "capacity_step320_observation.json").write_text(json.dumps(obs, ensure_ascii=False, indent=2) + "\n")
    (HERE / "capacity_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"pass": result["pass"], "checks": checks,
                      "baseline_build_tasks": baseline["build_tasks"], "capacity_tasks": patched["build_tasks"],
                      "branches": [{"label": b["label"], "last": b["rows"][-1]} for b in branches]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
