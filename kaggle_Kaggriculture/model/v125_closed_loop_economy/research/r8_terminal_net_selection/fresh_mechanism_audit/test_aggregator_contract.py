"""纯合成算式核验，不读取比赛，不调用引擎或候选。"""
import copy,hashlib,importlib.util,json
from pathlib import Path
p=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("r8_mechanism",p/"assess_first_sale_mechanism.py");m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def row(t,no=False):return {"source_key":"synthetic","first_sale":{"status":"NUMERIC_COMPLETE","restricted_elapsed_decisions":t,"no_qualifying_sale":no,"first_sale_step":None if no else t-1}}
checks=[]
def ok(name,value):assert value,name;checks.append(name)
a=m.measure([row(100)]*6);b=m.measure([row(80)]*6)
ok("exact_20pct_integer_boundary",m.numeric_decision(a,b) is True)
ok("less_than_20pct_fails",m.numeric_decision(a,m.measure([row(81)]*6)) is False)
z=m.measure([row(719,True)]*6);ok("no_event_719_all_in_denominator",z["T"]==719 and z["elapsed_sum"]==4314 and z["no_event_count"]==6)
v=[row(100)]*5+[row(719,True)];ok("no_event_not_dropped",m.measure(v)["T"]==1219/6)
v=copy.deepcopy(v);v[0]["first_sale"]["status"]="PENDING_PROVENANCE";v[0]["first_sale"]["restricted_elapsed_decisions"]=None
z=m.measure(v);ok("pending_not_zero_or_ignored",z["T"] is None and m.numeric_decision(a,z) is None)
ok("five_games_pending",m.measure([row(100)]*5)["status"]=="PENDING")
v=[row(100)]*5+[row(True)];ok("bool_clock_rejected",m.measure(v)["status"]=="PENDING")
v=[row(100)]*5+[row(720)];ok("out_of_horizon_rejected",m.measure(v)["status"]=="PENDING")
x=row(100);x["first_sale"]["first_sale_step"]=100;ok("step_plus_one_checked",m.measure([x]*6)["status"]=="PENDING")
x=row(718,True);ok("no_event_requires_719",m.measure([x]*6)["status"]=="PENDING")
# 分席约束独立于总量：前席从100变110、后席100变20，组改进35%，前席仍变晚。
ok("per_seat_guard_cannot_be_averaged_away",m.numeric_decision(a,m.measure([row(110)]*3+[row(20)]*3)) is True and 330>300)
result={"checks":checks,"all_pass":True,"synthetic_only":True,"candidate_calls":0,"engine_steps":0,"new_independent_matches":0,"aggregator_sha256":m.sha(m.__file__)}
(p/"contract_validation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(result,ensure_ascii=False,indent=2))
