#!/usr/bin/env python3
"""R0 任务依赖人工反例。只执行最多六帧；不打开 Replay、不跑完整比赛。"""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

import run_microcases as engine

HERE = Path(__file__).resolve().parent
EXPECTED_R0 = "9898f724bd71abc91520c7ea29ac90734507236c2fa4237af76a5d87dad404fe"


def load():
    p = HERE / "snapshot/v125_r0_main.py"
    assert engine.sha(p) == EXPECTED_R0
    spec = importlib.util.spec_from_file_location("r0_dependency_diagnostic", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def setup(seat, scenario):
    env, _ = engine.setup(seat, "fully_funded_control")
    day, hour = (29, 22) if scenario == "terminal_mixed_cargo" else (11, 21 if scenario == "at_crop_fertilizer_deadline_blocks" else 18)
    public = env.state[0].observation
    for f in public.farms:
        f["farmer"], f["hands"], f["hires_today"], f["money"] = [0, 0], [], 0, 0
        f["unlocked_quadrants"] = ["NW"]
        f["tiles"] = [[None if x < 5 and y < 5 else "LOCKED" for x in range(10)] for y in range(10)]
    public.town["unlocked_shops"] = []
    for s in env.state:
        s.observation.step = day * 24 + hour
        s.observation.day, s.observation.hour = day, hour
        s.observation.private["shed"] = {}
        s.observation.private["seeds"] = {}
        s.observation.private["inventories"] = [{}]
    farm, private = public.farms[seat], env.state[seat].observation.private
    if scenario == "terminal_mixed_cargo":
        farm["farmer"] = [4, 4]
        private["inventories"] = [{"MELON": 1, "MILK": 1, "WOOL": 1}]
    else:
        crop = engine.RULES._new_plant("STRAWBERRY", 0, 24)
        crop.update(consecutive_unwatered=1, yield_units=1)
        farm["tiles"][0][0] = crop
        farm["hands"], farm["hires_today"] = [[4, 4]], 1
        private["inventories"] = [{}, {"FERTILIZER": 1}]
        if scenario == "no_fertilizer_control":
            private["inventories"][1] = {}
        elif scenario in ("fertilizer_at_crop_control", "at_crop_fertilizer_deadline_blocks"):
            private["inventories"] = [{"FERTILIZER": 1}, {}]
    return env


def compact(obs, seat):
    f = obs["farms"][seat]
    return {**engine.compact(obs), "crop": deepcopy(f["tiles"][0][0]),
            "farmer": f["farmer"], "hands": f["hands"]}


def play(seat, scenario, mode="r0"):
    mod = load()
    env = setup(seat, scenario)
    initial = engine.observed(env, seat)
    rows = []
    for _ in range(1 if scenario == "terminal_mixed_cargo" else 24 - initial["hour"]):
        obs = engine.observed(env, seat)
        action = mod.agent(obs)
        r0_action = deepcopy(action)
        # 可行操作对照不是候选策略。它只证明同一状态下引擎允许保活/采收。
        if mode == "feasible_crop_control":
            if obs["hour"] == initial["hour"]:
                action["farmer"] = ["WATER"]
            elif obs["hour"] == initial["hour"] + 1:
                action["farmer"] = ["HARVEST"]
        elif mode == "feasible_terminal_control":
            action["farmer"] = ["DROP"]
            action["market"] = [["SELL", p, n] for p, n in obs["private"]["inventories"][0].items()]
        state = mod._STATES[seat]
        plan = mod.economic_plan(obs, state)
        tasks = mod.make_tasks(obs, state, plan)
        pair = [deepcopy(engine.PASS), deepcopy(engine.PASS)]
        pair[seat] = action
        engine.official_step(env, pair)
        nxt = engine.observed(env, seat)
        rows.append({"input": compact(obs, seat), "r0_action": r0_action,
                     "applied_action": deepcopy(action), "tasks": tasks,
                     "output": compact(nxt, seat), "status": env.state[seat].status})
    return {"scenario": scenario, "seat": seat, "mode": mode,
            "initial_observation": initial, "rows": rows,
            "final": compact(engine.observed(env, seat), seat)}


def main():
    assert engine.sha(engine.RULES.__file__) == engine.EXPECTED_RULES_SHA
    runs = [play(seat, case) for seat in (0, 1) for case in
            ("remote_fertilizer_blocks_crop", "no_fertilizer_control", "fertilizer_at_crop_control", "at_crop_fertilizer_deadline_blocks", "terminal_mixed_cargo")]
    runs += [play(seat, "remote_fertilizer_blocks_crop", "feasible_crop_control") for seat in (0, 1)]
    runs += [play(seat, "at_crop_fertilizer_deadline_blocks", "feasible_crop_control") for seat in (0, 1)]
    runs += [play(seat, "terminal_mixed_cargo", "feasible_terminal_control") for seat in (0, 1)]
    checks = {}
    for seat in (0, 1):
        get = lambda scenario, mode="r0": next(r for r in runs if r["seat"] == seat and r["scenario"] == scenario and r["mode"] == mode)
        blocked = get("remote_fertilizer_blocks_crop")
        nofert = get("no_fertilizer_control")
        atcrop = get("fertilizer_at_crop_control")
        feasible = get("remote_fertilizer_blocks_crop", "feasible_crop_control")
        deadline = get("at_crop_fertilizer_deadline_blocks")
        deadline_feasible = get("at_crop_fertilizer_deadline_blocks", "feasible_crop_control")
        terminal = get("terminal_mixed_cargo")
        drop = get("terminal_mixed_cargo", "feasible_terminal_control")
        checks[f"seat{seat}_fertility_blocks_near_worker"] = blocked["rows"][0]["r0_action"]["farmer"] == ["PASS"]
        checks[f"seat{seat}_remote_fertilizer_crop_dies"] = blocked["final"]["crop"]["kind"] == "WEED"
        checks[f"seat{seat}_no_fertilizer_crop_survives"] = nofert["final"]["crop"]["kind"] == "PLANT"
        checks[f"seat{seat}_same_fertilizer_at_crop_survives"] = atcrop["final"]["crop"]["kind"] == "PLANT"
        checks[f"seat{seat}_identical_state_feasible_water_harvest"] = feasible["initial_observation"] == blocked["initial_observation"] and feasible["final"]["crop"]["kind"] == "PLANT" and feasible["final"]["shed"].get("STRAWBERRY", 0) == 1
        checks[f"seat{seat}_full_chain_deadline_blocks_feasible_water"] = deadline["rows"][0]["r0_action"]["farmer"] == ["PASS"] and deadline["final"]["crop"]["kind"] == "WEED" and deadline_feasible["initial_observation"] == deadline["initial_observation"] and deadline_feasible["final"]["crop"]["kind"] == "PLANT"
        checks[f"seat{seat}_terminal_mixed_cargo_left"] = len(terminal["final"]["inventories"][0]) == 2
        checks[f"seat{seat}_terminal_drop_control_more_money"] = drop["final"]["money"] > terminal["final"]["money"] and not drop["final"]["inventories"][0]
    checks["all_clock_transitions_exact"] = all(row["output"]["step"] == row["input"]["step"]+1 and row["output"]["step"] == 24*row["output"]["day"]+row["output"]["hour"] for r in runs for row in r["rows"])
    result = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
              "method": "人工局部状态；完整官方解释器；自然发生频率未知；操作对照不是新策略候选",
              "source_sha256": EXPECTED_R0, "engine_sha256": engine.sha(engine.RULES.__file__),
              "harness_sha256": engine.sha(__file__), "engine_scaffold_sha256": engine.sha(engine.__file__),
              "replay_reads": 0, "blind_reads": 0, "workers": 1,
              "interpreter_transitions": sum(len(r["rows"]) for r in runs),
              "checks": checks, "pass": all(checks.values()), "runs": runs}
    (HERE/"dependency_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"pass": result["pass"], "checks": checks,
                      "runs": [{"case": r["scenario"], "seat": r["seat"], "mode": r["mode"], "first_action": r["rows"][0]["applied_action"], "final": r["final"]} for r in runs]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
