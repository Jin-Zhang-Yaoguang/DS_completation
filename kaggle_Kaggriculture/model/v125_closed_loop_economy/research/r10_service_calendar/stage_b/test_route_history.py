"""完整 route 对冻结 compiler 已知不可能首水历史的独立负控。"""
from pathlib import Path
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import calendar_compiler as compiler
import route_admission as route
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
private={'shed':{},'inventories':[{}],'seeds':{}}
impossible=compiler.project_calendar_with_services({'kind':'PLANT','crop':'WHEAT','planted_day':0,
    'yield_units':1,'consecutive_unwatered':1,'watered_today':False,'fertilized_until_day':-1,
    'max_lifespan_step':120},0,24,(3,4),{'kind':'known_impossible_h24_control'})
others=[]
for y in range(10):
    for x in range(10):
        if min(x,y,9-x,9-y)<=1:
            others.append(compiler.project_calendar_with_services({'kind':'PLANT','crop':'MELON','planted_day':0,
                'yield_units':1,'consecutive_unwatered':0,'watered_today':True,'fertilized_until_day':-1,
                'max_lifespan_step':312},0,7,(x,y),{'kind':'artificial_current_watered_asset'}))
cals=[impossible,*others]
aggregate=route.aggregate_calendars(cals)
capacity,costs={},{}
fib=[1,1,2,3,5,8,13,21,34,55,89,144]
for d in range(30):
    slots=24 if d<29 else 23
    cap=slots; n=0
    while cap<aggregate['work'].get(d,0) and n<12:
        cap+=slots-(1 if n<10 else 2); n+=1
    capacity[d]=cap;costs[d]=sum(fib[:n])
labor={'feasible':all(aggregate['work'].get(d,0)<=capacity[d] for d in range(30)),
    'hire_target_today':0,'cash_by_day':costs,'capacity_by_day':capacity,'total_cost':sum(costs.values())}
zero={d:0 for d in range(30)}
p={'calendars':cals,'coverage_asset_ids':[c['asset_id'] for c in cals], 'legacy_aggregate':aggregate,
    'workload':deepcopy(aggregate['work']),'labor':labor,'funding_requirements':dict(zero),
    'funding_feed':{'buys_by_day':dict(zero),'stock_by_day':dict(zero),'cash_by_day':dict(zero),'total_cash':0},
    'startup_fallback_days':[0], 'pending_animal_units':{},'conditional_prior_product_sales':True}
before=deepcopy(p)
ids={n:sha(HERE/(n+'.py')) for n in ('scheduler','checker')};ids['compiler']=sha(HERE/'calendar_compiler.py')
cache=route.PlanRouteCache('history-control',0,private)
result=route.route_admission(p,p,current_day=0,observed_private=private,plan_token='history-control',cache=cache,implementation_ids=ids)
raw_day2=compiler.compile_day_problem([impossible],2,0,{}, {},
    {'qty':0,'estimated_cash':0,'order_hour':0,'available_from_hour':1},impossible['work'].get(2,0),376,startup_fallback_days=[0])
checks={
 'real_compiler_records_h24_h23_conflict':impossible['services'][0][0]['release']==24 and impossible['services'][0][0]['deadline']==23,
 'raw_compiler_future_still_supported':raw_day2['status']=='SUPPORTED',
 'old_current_labor_feasible':aggregate['work'].get(0,0)<=capacity[0],
 'first_legacy_failure_is_day2':next(d for d in range(30) if aggregate['work'].get(d,0)>capacity[d])==2,
 'complete_route_rejects_bad_history':not result['labor_feasible_after_routes'] and result['failed_day']==2 and 'KNOWN_IMPOSSIBLE_CALENDAR_HISTORY:plant:WHEAT:0:3,4:d0' in result['reason'],
 'no_solver_or_checker_call':result['scheduler_calls']==result['checker_calls']==0,
 'no_partial_cache_or_input_mutation':not cache.entries and p==before,
}
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
report={'checks':checks,'passed':sum(checks.values()),'check_count':len(checks),'all_passed':all(checks.values()),
    'result':result,'raw_day2_status':raw_day2['status'],'impossible_calendar':impossible,
    'source_sha256':{n:sha(HERE/n) for n in ('route_admission.py','calendar_compiler.py','test_route_history.py')},
    'counts':{'enriched_calendar_calls':65,'raw_day_compiler_calls':1,'route_calls':1,'scheduler_calls':0,'checker_calls':0,
        'candidate_calls':0,'official_calls':0,'new_complete_matches':0},
    'boundary':'Current-other-assets are artificial visible states; test isolates history guard, not natural whole-game reachability.'}
path=HERE/('route_history_tests_'+stamp+'.json');path.write_text(json.dumps(report,indent=2,ensure_ascii=False))
print(json.dumps({'path':str(path),'checks':len(checks),'passed':sum(checks.values()),'failed':[k for k,v in checks.items() if not v]},ensure_ascii=False))
assert all(checks.values())
