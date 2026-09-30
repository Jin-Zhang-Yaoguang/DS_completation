"""冻结 R4 的工人相对紧迫性反例；失败归因用，不修改候选。"""
from pathlib import Path
import json
import test_microcases as t

HERE=Path(__file__).resolve().parent
FROZEN="8d3b634468d58c47df7c2c87644af04aa9d493e7c6381969866d4acfa3558431"

def main():
    assert t.scaffold.engine.sha(HERE/"main.py")==FROZEN
    runs=[]
    for ready in (0,1):
        env=t.empty_env(day=11,hour=15);farm=env.state[0].observation.farms[0]
        farm["farmer"],farm["hands"],farm["hires_today"]=[0,0],[[4,4]],1
        env.state[0].observation.private["inventories"]=[{},{}]
        plant=t.scaffold.engine.RULES._new_plant("STRAWBERRY",0,24)
        plant.update(consecutive_unwatered=1,yield_units=ready);farm["tiles"][0][0]=plant
        mod=t.load();obs=t.scaffold.engine.observed(env,0);st=mod.new_state(obs)
        plan=mod.economic_plan(obs,st);groups=mod.compile_contracts(obs,st,mod.make_tasks(obs,st,plan))
        bonus=1+sum(max(0,s["value"]) for g in groups for s in g["stages"])
        offers=[mod.propose_contract(obs,u,groups[0],dict(obs["private"]["shed"])) for u in (0,1)]
        weights=[sum(s["value"] for s in offer["stages"])/offer["cost"]*(1.15 if u==0 else 1)+(bonus if offer["urgent"] else 0) for u,offer in enumerate(offers)]
        result,_=t.run(env,0,9,"worker_relative_urgency_yield"+str(ready))
        result.update(initial_offers=offers,urgent_bonus=bonus,assignment_weights=weights)
        runs.append(result)
    result={"status":"CONFIRMED_WITH_READY_FRUIT_CONTROLLED_COUNTEREXAMPLE","source_sha256":FROZEN,
            "harness_sha256":t.scaffold.engine.sha(__file__),"engine_sha256":t.scaffold.engine.sha(t.scaffold.engine.RULES.__file__),
            "method":"冻结R4原码，人工单目标两工人，yield0/1控制，完整官方解释器18次转换；非新seed完整比赛",
            "replay_reads":0,"blind_reads":0,"workers":1,"runs":runs,
            "checks":{"yield0_near_worker_control":runs[0]["rows"][0]["applied"]["farmer"]==["WATER"],
                      "yield1_far_worker_chosen":runs[1]["rows"][0]["applied"]["farmer"]==["PASS"] and runs[1]["rows"][0]["applied"]["hands"]==[["WEST"]],
                      "eight_walks_instead_of_immediate_water":sum(r["applied"]["hands"][0][0] in ("WEST","NORTH") for r in runs[1]["rows"])==8,
                      "near_worker_idle_nine_frames":all(r["applied"]["farmer"]==["PASS"] for r in runs[1]["rows"])}}
    (HERE/"worker_relative_urgency_failure.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"checks":result["checks"],"weights":[r["assignment_weights"] for r in runs]},ensure_ascii=False))

if __name__=="__main__":main()
