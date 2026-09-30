"""R5 只检验共享紧迫性与owner互斥，不运行新seed完整比赛。"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timezone
import ast,hashlib,importlib.util,json,sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"r4_contract_design"))
import test_microcases as common


def load(parent=False):
    path=HERE/("parent_r4.py" if parent else "main.py")
    spec=importlib.util.spec_from_file_location("r5_module",path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def run(env,n,name,mod=None):
    return common.run(env,0,n,name,module=mod or load())


def plant(env,x,y,crop="STRAWBERRY",planted=0,**kw):
    t=common.scaffold.engine.RULES._new_plant(crop,planted,24);t.update(kw);env.state[0].observation.farms[0]["tiles"][y][x]=t;return t


def animal(env,x,y,**kw):
    t=common.scaffold.engine.RULES._new_animal("COW",0);t.update(kw);env.state[0].observation.farms[0]["tiles"][y][x]=t;return t


def stage_urgency(mod,obs):
    st=mod.new_state(obs);plan=mod.economic_plan(obs,st);groups=mod.compile_contracts(obs,st,mod.make_tasks(obs,st,plan))
    return mod.shared_task_urgency(obs,range(1+len(obs["farms"][0]["hands"])),groups,dict(obs["private"]["shed"]))


def main():
    checks,runs={},[]
    env=common.empty_env(day=11,hour=15);f=env.state[0].observation.farms[0]
    f["hands"],f["hires_today"]=[[4,4]],1;env.state[0].observation.private["inventories"]=[{},{}]
    plant(env,0,0,consecutive_unwatered=1,yield_units=1)
    parent,_=run(deepcopy(env),1,"r4_far_worker_regression",load(True));runs.append(parent)
    r,m=run(env,2,"r5_near_worker_handles_water_and_harvest");runs.append(r)
    checks["original_r4_counterexample_reproduced"]=parent["rows"][0]["applied"]["farmer"]==["PASS"] and parent["rows"][0]["applied"]["hands"]==[["WEST"]]
    checks["r5_near_worker_no_distance_reward"]=[x["applied"]["farmer"] for x in r["rows"]]==[["WATER"],["HARVEST"]] and all(x["applied"]["hands"]==[["PASS"]] for x in r["rows"])
    checks["task_not_urgent_when_near_worker_available"]=stage_urgency(load(),r["initial_observation"])[(0,0)] is False

    env=common.empty_env(day=11,hour=15);env.state[0].observation.farms[0]["farmer"]=[4,4]
    plant(env,0,0,consecutive_unwatered=1,yield_units=1)
    r,m=run(env,9,"only_far_worker_available");runs.append(r)
    checks["only_far_worker_task_really_urgent"]=stage_urgency(load(),r["initial_observation"])[(0,0)] is True and r["rows"][-1]["applied"]["farmer"]==["WATER"] and r["final"]["farms"][0]["tiles"][0][0]["kind"]=="PLANT"

    env=common.empty_env(day=11,hour=22);env.state[0].observation.farms[0]["farmer"]=[1,0]
    plant(env,0,0,consecutive_unwatered=1,yield_units=0)
    plant(env,1,0,"MELON",watered_today=True,consecutive_unwatered=0,yield_units=6)
    r,m=run(env,2,"true_deadline_beats_immediate_optional_harvest");runs.append(r)
    checks["true_last_window_gets_shared_priority"]=[x["applied"]["farmer"] for x in r["rows"]]==[["WEST"],["WATER"]] and m._STATES[0]["metrics"]["confirmed_WATER"]==1

    env=common.empty_env(day=11,hour=22);env.state[0].observation.farms[0]["farmer"]=[1,0]
    plant(env,0,0,consecutive_unwatered=1,yield_units=0)
    plant(env,1,0,"MELON",watered_today=True,consecutive_unwatered=0,yield_units=6)
    env.state[0].observation.market["inventory"]["MELON"]=-10000000
    common.scaffold.engine.RULES._refresh_prices(env.state[0].observation.market)
    r,m=run(env,2,"strict_urgency_upper_bound_includes_at_target_bonus");runs.append(r)
    checks["strict_priority_beats_large_present_harvest_with_115pct_bonus"]=[x["applied"]["farmer"] for x in r["rows"]]==[["WEST"],["WATER"]]

    for water_owner in (0,1):
        env=common.empty_env(day=11,hour=22);f=env.state[0].observation.farms[0]
        f["farmer"],f["hands"],f["hires_today"]=[1,0],[[1,0]],1
        env.state[0].observation.private["inventories"]=[{},{}]
        plant(env,0,0,consecutive_unwatered=1,yield_units=0);animal(env,1,0,fed_today=True)
        mod=load();obs=common.scaffold.engine.observed(env,0)
        common.prime_contract(mod,obs,water_owner,(0,0));common.prime_contract(mod,obs,1-water_owner,(1,0))
        r,m=run(env,1,"all_owners_visible_water_owner"+str(water_owner),mod);runs.append(r)
        commands=[r["rows"][0]["applied"]["farmer"],*r["rows"][0]["applied"]["hands"]]
        checks["owner_order_"+str(water_owner)+"_no_false_preemption"]=commands[water_owner]==["WEST"] and commands[1-water_owner]==["CARE"] and m._STATES[0]["metrics"]["contract_urgent_preempted"]==0

    # 同一个目标的可选收获边不是紧迫FEED的可行边。
    env=common.empty_env(day=11,hour=23);f=env.state[0].observation.farms[0]
    f["hands"],f["hires_today"]=[[0,0]],1;env.state[0].observation.private["inventories"]=[{}, {"WHEAT":1}]
    animal(env,0,0,consecutive_unfed=1,yield_units=6)
    r,m=run(env,1,"only_feed_capable_edge_receives_urgent_bonus");runs.append(r)
    checks["optional_harvest_does_not_steal_shared_feed_priority"]=r["rows"][0]["applied"]["hands"]==[["FEED"]] and r["final"]["farms"][0]["tiles"][0][0].get("animal")=="COW" and m._STATES[0]["metrics"]["confirmed_FEED"]==1

    # 可选旧合同不能把同格紧迫FEED错误标成已有覆盖。
    env=common.empty_env(day=11,hour=23);f=env.state[0].observation.farms[0]
    f["hands"],f["hires_today"]=[[0,0]],1;env.state[0].observation.private["inventories"]=[{}, {"WHEAT":1}]
    animal(env,0,0,consecutive_unfed=1,yield_units=6)
    mod=load();obs=common.scaffold.engine.observed(env,0);common.prime_contract(mod,obs,0,(0,0))
    r,m=run(env,1,"old_harvest_owner_does_not_cover_urgent_feed",mod);runs.append(r)
    checks["only_real_necessary_stage_counts_as_coverage"]=r["rows"][0]["applied"]["hands"]==[["FEED"]] and m._STATES[0]["metrics"]["contract_urgent_goal_not_covered"]==1

    # 刚完成播种的WATER合同，不因远端候选的虚假零slack而放弃首水。
    env=common.empty_env(day=11,hour=20);f=env.state[0].observation.farms[0]
    f["hands"],f["hires_today"]=[[3,0]],1;env.state[0].observation.private["inventories"]=[{"WHEAT":1},{"WHEAT":1}]
    plant(env,0,0,"MELON",planted=11,consecutive_unwatered=1);animal(env,3,0,consecutive_unfed=1)
    mod=load();obs=common.scaffold.engine.observed(env,0);common.prime_contract(mod,obs,0,(0,0))
    r,m=run(env,1,"first_water_contract_not_preempted_by_far_offer",mod);runs.append(r)
    checks["first_water_retained_when_other_task_has_near_worker"]=r["rows"][0]["applied"]["farmer"]==["WATER"] and r["rows"][0]["applied"]["hands"]==[["FEED"]] and m._STATES[0]["metrics"]["contract_urgent_preempted"]==0

    old=ast.parse((HERE/"parent_r4.py").read_text());new=ast.parse((HERE/"main.py").read_text())
    funcs=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    oldf,newf=funcs(old),funcs(new)
    changed=[k for k in oldf if oldf[k]!=newf[k]]
    checks["only_allocate_changed_and_shared_urgency_added"]=changed==["allocate"] and set(newf)-set(oldf)=={"shared_task_urgency"}
    checks["all_clocks_exact"]=all(row["output"]["step"]==row["step"]+1 for rr in runs for row in rr["rows"])
    output={"created_at_utc":datetime.now(timezone.utc).isoformat(),"candidate_sha256":common.scaffold.engine.sha(HERE/"main.py"),
        "parent_sha256":common.scaffold.engine.sha(HERE/"parent_r4.py"),"harness_sha256":common.scaffold.engine.sha(__file__),
        "engine_sha256":common.scaffold.engine.sha(common.scaffold.engine.RULES.__file__),"checks":checks,"pass":all(checks.values()),
        "workers":1,"replay_reads":0,"blind_reads":0,"new_full_games":0,"runs":runs}
    (HERE/"micro_results.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"pass":output["pass"],"checks":checks,"runs":len(runs),"transitions":sum(len(r["rows"]) for r in runs)},ensure_ascii=False))

if __name__=="__main__":main()
