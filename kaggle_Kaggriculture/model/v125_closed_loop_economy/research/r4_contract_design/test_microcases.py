#!/usr/bin/env python3
"""合约机制短场景；只读既有微场景定义，无新 Replay 或完整新比赛。"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "procurement_audit"))
import run_dependency_microcases as scaffold


def load():
    spec = importlib.util.spec_from_file_location("r4_micro", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def set_time(env, day, hour):
    for s in env.state:
        s.observation.step, s.observation.day, s.observation.hour = day * 24 + hour, day, hour


def empty_env(seat=0, day=11, hour=18):
    env = scaffold.setup(seat, "no_fertilizer_control")
    farm = env.state[0].observation.farms[seat]
    farm["tiles"] = [[None if x < 5 and y < 5 else "LOCKED" for x in range(10)] for y in range(10)]
    farm["farmer"], farm["hands"], farm["hires_today"] = [0, 0], [], 0
    p = env.state[seat].observation.private
    p["inventories"], p["shed"], p["seeds"] = [{}], {}, {}
    set_time(env, day, hour)
    return env


def run(env, seat, count, name, override=None, module=None):
    mod, rows = module or load(), []
    initial = scaffold.engine.observed(env, seat)
    for i in range(count):
        obs = scaffold.engine.observed(env, seat)
        action = mod.agent(obs)
        dispatched = deepcopy(action)
        pending = deepcopy(mod._STATES[seat].get("contracts", {}))
        if override:
            override(i, env, action, mod)
        pair = [deepcopy(scaffold.engine.PASS), deepcopy(scaffold.engine.PASS)]
        pair[seat] = action
        scaffold.engine.official_step(env, pair)
        rows.append({"step": obs["step"], "dispatched": dispatched, "applied": deepcopy(action),
                     "pending_after_dispatch": pending, "metrics_after_dispatch": dict(mod._STATES[seat]["metrics"]),
                     "output": scaffold.engine.observed(env, seat)})
    final = scaffold.engine.observed(env, seat)
    # 只核对最后动作收据，不再多执行一个回合。
    mod.confirm_execution(mod._STATES[seat], final)
    return {"name": name, "seat": seat, "initial_observation": initial, "rows": rows,
            "final": final, "diagnostics": mod.diagnostics()}, mod


def tile(run, x=0, y=0):
    return run["final"]["farms"][run["seat"]]["tiles"][y][x]


def prime_contract(mod, obs, unit, target):
    st=mod._STATES.setdefault(obs["player"],mod.new_state(obs))
    st["last_step"]=obs["step"]-1
    plan=mod.economic_plan(obs,st);groups=mod.compile_contracts(obs,st,mod.make_tasks(obs,st,plan))
    offer=mod.propose_contract(obs,unit,next(g for g in groups if g["target"]==target),dict(obs["private"]["shed"]))
    assert offer
    st.setdefault("contracts",{})[unit]={"owner":unit,"target":target,"kind":offer["kind"],"fingerprint":offer["fingerprint"],
        "stages":deepcopy(offer["stages"]),"day":obs["day"],"accepted_step":obs["step"]-1,"expires":obs["step"]+offer["cost"],"phase":"ready","receipt":None}


def main():
    checks, runs = {}, []
    for seat in (0, 1):
        for case in ("remote_fertilizer_blocks_crop", "no_fertilizer_control", "fertilizer_at_crop_control", "at_crop_fertilizer_deadline_blocks"):
            env = scaffold.setup(seat, case)
            result, mod = run(env, seat, 24 - env.state[seat].observation.hour, case)
            runs.append(result)
            checks[f"s{seat}_{case}_survives"] = tile(result).get("kind") == "PLANT"
            checks[f"s{seat}_{case}_harvest_delivered"] = result["final"]["private"]["shed"].get("STRAWBERRY",0) == 1
            if case == "at_crop_fertilizer_deadline_blocks":
                checks[f"s{seat}_crossday_harvest_not_falsely_confirmed"] = mod._STATES[seat]["metrics"]["confirmed_HARVEST"] == 0 and mod._STATES[seat]["metrics"]["receipt_unknown"] == 1
            if case in ("fertilizer_at_crop_control", "at_crop_fertilizer_deadline_blocks"):
                checks[f"s{seat}_{case}_fertility_preserved"] = result["rows"][0]["dispatched"]["farmer"] == ["FERTILIZE"] and tile(result)["yield_units"] == 2

        env = empty_env(seat, hour=23)
        plant = scaffold.engine.RULES._new_plant("STRAWBERRY", 0, 24)
        plant.update(consecutive_unwatered=1, yield_units=1)
        env.state[0].observation.farms[seat]["tiles"][0][0] = plant
        result, mod = run(env, seat, 1, "last_frame_water")
        runs.append(result)
        checks[f"s{seat}_last_frame_water_confirmed"] = result["rows"][0]["applied"]["farmer"] == ["WATER"] and tile(result)["kind"] == "PLANT" and mod._STATES[seat]["metrics"]["confirmed_WATER"] == 1

        env = empty_env(seat, hour=23)
        animal = scaffold.engine.RULES._new_animal("COW", 0)
        animal.update(consecutive_unfed=1, yield_units=2, fertilizer_available=True)
        env.state[0].observation.farms[seat]["tiles"][0][0] = animal
        env.state[seat].observation.private["inventories"] = [{"WHEAT": 1}]
        result, mod = run(env, seat, 1, "last_frame_feed")
        runs.append(result)
        checks[f"s{seat}_last_frame_feed_confirmed"] = result["rows"][0]["applied"]["farmer"] == ["FEED"] and tile(result).get("animal") == "COW" and mod._STATES[seat]["metrics"]["confirmed_FEED"] == 1

        env = empty_env(seat, hour=20)
        animal = scaffold.engine.RULES._new_animal("COW", 0)
        animal.update(yield_units=2, fertilizer_available=True)
        env.state[0].observation.farms[seat]["tiles"][0][0] = animal
        result, mod = run(env, seat, 2, "no_wheat_can_harvest")
        runs.append(result)
        checks[f"s{seat}_unavailable_feed_does_not_block_harvest"] = result["rows"][0]["applied"]["farmer"] == ["HARVEST"] and mod._STATES[seat]["metrics"]["confirmed_HARVEST"] == 1 and mod._STATES[seat]["metrics"]["confirmed_FEED"] == 0

        env = scaffold.setup(seat, "fertilizer_at_crop_control")
        result, mod = run(env, seat, 2, "rejected_request_not_confirmed", lambda i,e,a,m: a.update(farmer=["PASS"]) if i == 0 else None)
        runs.append(result)
        checks[f"s{seat}_dispatch_is_not_completion"] = result["rows"][0]["metrics_after_dispatch"].get("confirmed_FERTILIZE", 0) == 0 and result["rows"][1]["metrics_after_dispatch"].get("receipt_failed", 0) == 1 and result["rows"][1]["dispatched"]["farmer"] == ["FERTILIZE"]

        for op in ("WATER", "FEED"):
            env = empty_env(seat,hour=23)
            farm = env.state[0].observation.farms[seat]
            farm["farmer"],farm["hands"],farm["hires_today"]=[4,4],[[0,0]],1
            target = scaffold.engine.RULES._new_plant("STRAWBERRY",0,24) if op=="WATER" else scaffold.engine.RULES._new_animal("COW",0)
            target["consecutive_unwatered" if op=="WATER" else "consecutive_unfed"]=1
            farm["tiles"][0][0]=target
            env.state[seat].observation.private["inventories"]=[{},{} if op=="WATER" else {"WHEAT":1}]
            result,mod=run(env,seat,1,"hand_last_frame_"+op)
            runs.append(result)
            checks[f"s{seat}_hand_{op}_confirmed_before_owner_reset"] = result["rows"][0]["applied"]["hands"]==[[op]] and not result["final"]["farms"][seat]["hands"] and mod._STATES[seat]["metrics"]["confirmed_"+op]==1 and not mod._STATES[seat].get("contracts")

    # 真正取得施工后续种子额度后才允许两块杂草中的一块开工。
    env = empty_env(day=12, hour=10)
    farm = env.state[0].observation.farms[0]
    farm["farmer"], farm["hands"], farm["hires_today"] = [0, 0], [[1, 0]], 1
    farm["tiles"][0][0], farm["tiles"][0][1] = {"kind": "WEED"}, {"kind": "WEED"}
    env.state[0].observation.private["inventories"] = [{}, {}]
    mod = load()
    obs = scaffold.engine.observed(env, 0)
    st = mod.new_state(obs); plan = mod.economic_plan(obs, st)
    crop = st["crop_choice"]
    env.state[0].observation.private["seeds"] = {crop: 1}
    result, mod = run(env, 0, 1, "seed_reserved_before_dig")
    runs.append(result)
    reservations = [c for c in result["rows"][0]["pending_after_dispatch"].values() if any(s["op"][0] == "PLANT" for s in c["stages"])]
    checks["only_one_investment_contract_per_seed"] = len(reservations) == 1

    # 低编号放货不能借高编号稍后 PICKUP 才释放的仓容。
    env = empty_env(day=12, hour=10)
    farm = env.state[0].observation.farms[0]
    farm["farmer"], farm["hands"], farm["hires_today"] = [4, 4], [[4, 4]], 1
    animal = scaffold.engine.RULES._new_animal("COW", 0)
    farm["tiles"][3][4] = animal
    env.state[0].observation.private["inventories"] = [{"MELON": 1}, {}]
    env.state[0].observation.private["shed"] = {"WHEAT": 100}
    mod=load();prime_contract(mod,scaffold.engine.observed(env,0),1,(4,3))
    result, mod = run(env, 0, 1, "full_shed_execution_order",module=mod)
    runs.append(result)
    checks["does_not_borrow_future_pickup_capacity"] = result["rows"][0]["applied"]["hands"]==[["PICKUP","WHEAT",1]] and result["rows"][0]["applied"]["farmer"]==["PASS"] and result["final"]["private"]["inventories"][0].get("MELON")==1

    env=empty_env(day=11,hour=22);farm=env.state[0].observation.farms[0]
    farm["hands"],farm["hires_today"]=[[1,0]],1;env.state[0].observation.private["inventories"]=[{},{}]
    plant=scaffold.engine.RULES._new_plant("STRAWBERRY",0,24);plant.update(consecutive_unwatered=1,yield_units=0)
    animal=scaffold.engine.RULES._new_animal("COW",0);animal.update(fed_today=True)
    farm["tiles"][0][0],farm["tiles"][0][1]=plant,animal
    mod=load();obs=scaffold.engine.observed(env,0);prime_contract(mod,obs,0,(0,0));prime_contract(mod,obs,1,(1,0))
    result,mod=run(env,0,1,"owned_urgent_target_does_not_preempt",module=mod);runs.append(result)
    checks["owned_urgent_target_is_not_reassigned"] = result["rows"][0]["applied"]["farmer"]==["WATER"] and result["rows"][0]["applied"]["hands"]==[["CARE"]] and mod._STATES[0]["metrics"]["contract_urgent_preempted"]==0

    # 移动收据只确认路径推进；三步路不计成三次任务完成。
    env = empty_env(day=11, hour=18)
    farm = env.state[0].observation.farms[0]
    farm["farmer"] = [3, 0]
    plant = scaffold.engine.RULES._new_plant("STRAWBERRY", 0, 24)
    plant.update(consecutive_unwatered=1, yield_units=0)
    farm["tiles"][0][0] = plant
    result, mod = run(env, 0, 4, "stable_travel_contract")
    runs.append(result)
    checks["moving_contract_keeps_target"] = all(list(next(iter(r["pending_after_dispatch"].values()))["target"]) == [0,0] for r in result["rows"])
    checks["movement_not_counted_as_goal_completion"] = [r["applied"]["farmer"] for r in result["rows"]] == [["WEST"],["WEST"],["WEST"],["WATER"]] and mod._STATES[0]["metrics"]["contract_completed"] == 1 and mod._STATES[0]["metrics"]["confirmed_WATER"] == 1

    # 衰减边界当帧先 HARVEST 后衰减，从前一帧一格外出发仍可完成。
    env = empty_env(day=11, hour=20)
    farm = env.state[0].observation.farms[0]
    farm["farmer"] = [1,0]
    plant = scaffold.engine.RULES._new_plant("STRAWBERRY",0,24)
    plant.update(watered_today=True,consecutive_unwatered=0,yield_units=3,max_lifespan_step=11*24+21,fertilized_until_day=13)
    farm["tiles"][0][0] = plant
    result, mod = run(env,0,2,"harvest_on_lifespan_boundary")
    runs.append(result)
    checks["harvest_boundary_action_before_decay"] = [r["applied"]["farmer"] for r in result["rows"]] == [["WEST"],["HARVEST"]] and mod._STATES[0]["metrics"]["confirmed_HARVEST"]==1 and result["final"]["private"]["inventories"][0].get("STRAWBERRY")==3

    # 合法字段的人工报价冲击改变了新任务排序，已推进的两步保活合约仍完成。
    env=empty_env(day=11,hour=18);farm=env.state[0].observation.farms[0];farm["farmer"]=[1,0]
    left=scaffold.engine.RULES._new_plant("STRAWBERRY",0,24);left.update(consecutive_unwatered=1,yield_units=0)
    right=scaffold.engine.RULES._new_plant("WHEAT",7,24);right.update(watered_today=True,consecutive_unwatered=0,yield_units=6)
    farm["tiles"][0][0],farm["tiles"][0][4]=left,right
    def shock(i,e,a,m):
        if i==0:
            e.state[0].observation.market["inventory"]["WHEAT"]=-10000000
            scaffold.engine.RULES._refresh_prices(e.state[0].observation.market)
    result,mod=run(env,0,2,"stable_contract_despite_new_ranking",shock);runs.append(result)
    fresh_action=load().agent(result["rows"][0]["output"])
    checks["observed_progress_beats_nonurgent_reranking"] = [r["applied"]["farmer"] for r in result["rows"]]==[["WEST"],["WATER"]] and fresh_action["farmer"]!=["WATER"]

    env=empty_env(day=11,hour=18);farm=env.state[0].observation.farms[0]
    plant=scaffold.engine.RULES._new_plant("MELON",0,24);plant.update(watered_today=True,consecutive_unwatered=0,yield_units=6)
    farm["tiles"][0][0]=plant;env.state[0].observation.private["inventories"]=[{"FERTILIZER":1}]
    result,mod=run(env,0,2,"terminal_harvest_has_no_dead_object_tail");runs.append(result)
    checks["terminal_harvest_prunes_unreachable_fertilize"] = result["rows"][0]["applied"]["farmer"]==["HARVEST"] and result["rows"][1]["applied"]["farmer"]!=["FERTILIZE"] and mod._STATES[0]["metrics"]["receipt_failed"]==0 and not mod._STATES[0].get("contracts")

    # 已浇/已喂的 no-op，不能因为次日 counter 为零而被误认成新完成。
    mod = load()
    for op, flag, counter, material in (("WATER","watered_today","consecutive_unwatered",{}),("FEED","fed_today","consecutive_unfed",{"WHEAT":1})):
        before_tile = scaffold.engine.RULES._new_plant("STRAWBERRY", 0, 24) if op == "WATER" else scaffold.engine.RULES._new_animal("COW",0)
        before_tile[flag] = True
        after_tile = dict(before_tile); after_tile[flag]=False; after_tile[counter]=0
        before = {"step":287,"day":11,"position":(0,0),"inventory":material,"tile":before_tile}
        after = {"step":288,"day":12,"position":(4,4),"inventory":{},"tile":after_tile}
        checks[op+"_duplicate_cross_day_not_confirmed"] = mod._receipt_result({"action":[op],"before":before},after) != "confirmed"

    parent_ast = ast.parse((HERE/"parent_r3.py").read_text())
    current_ast = ast.parse((HERE/"main.py").read_text())
    for fn in ("economic_plan","market_orders","make_tasks","matching"):
        get = lambda tree: ast.dump(next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==fn),include_attributes=False)
        checks[fn+"_unchanged"] = get(parent_ast)==get(current_ast)
    checks["no_parent_import_or_parent_agent_call"] = not any(isinstance(x,(ast.Import,ast.ImportFrom)) and any("parent" in n.name for n in x.names) for x in ast.walk(current_ast))
    checks["raw_loader_entry_is_agent"] = [x.name for x in current_ast.body if isinstance(x,ast.FunctionDef)][-1] == "agent"
    checks["all_clocks_exact"] = all(r["output"]["step"]==r["step"]+1 for run_ in runs for r in run_["rows"])
    output = {"created_at_utc":datetime.now(timezone.utc).isoformat(),"candidate_sha256":scaffold.engine.sha(HERE/"main.py"),
              "parent_sha256":scaffold.engine.sha(HERE/"parent_r3.py"),"harness_sha256":scaffold.engine.sha(__file__),
              "engine_sha256":scaffold.engine.sha(scaffold.engine.RULES.__file__),"method":"人工观测短场景与结构核对；非强度验证；未运行新seed完整比赛",
              "workers":1,"replay_reads":0,"blind_reads":0,"checks":checks,"pass":all(checks.values()),"runs":runs}
    (HERE/"micro_results.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"pass":output["pass"],"checks":checks,"runs":len(runs),"transitions":sum(len(r["rows"]) for r in runs)},ensure_ascii=False))


if __name__ == "__main__":
    main()
