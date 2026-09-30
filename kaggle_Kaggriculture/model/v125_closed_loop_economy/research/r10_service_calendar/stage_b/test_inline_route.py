"""静态内联纯模块的完整准入结果等价；不是策略执行。"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import calendar_compiler as compiler
import route_admission as route
import inline_modules
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source,metadata=inline_modules.render(HERE)
sentinels={key:'parent-sentinel-'+key for key in ('CROPS','ANIMALS','PRODUCTS','ACCESS','Counter','math','canonical_sha')}
ns=dict(sentinels)
exec(compile(source,'static_owned_pure_modules','exec'),ns)
checks={'parent_globals_not_polluted':all(ns[k]==v for k,v in sentinels.items())}
private={'shed':{},'inventories':[{}],'seeds':{}}
cals=[]
for pos in [(x,y) for x in range(3) for y in range(4)]+[(9-x,9-y) for x in range(3) for y in range(4)]:
    cals.append(compiler.project_calendar_with_services({'kind':'PLANT','crop':'MELON','planted_day':18,
        'yield_units':1,'consecutive_unwatered':0,'watered_today':True,'fertilized_until_day':-1,
        'max_lifespan_step':744},28,7,pos))
aggregate=route.aggregate_calendars(cals)
base={'calendars':cals,'coverage_asset_ids':[c['asset_id'] for c in cals], 'legacy_aggregate':aggregate,
    'workload':deepcopy(aggregate['work']),
    'labor':{'feasible':False,'cash_by_day':{28:0,29:376},'capacity_by_day':{28:17,29:285},'total_cost':376,'hire_target_today':0},
    'funding_requirements':{28:3,29:0},
    'funding_feed':{'buys_by_day':{28:3,29:0},'stock_by_day':{28:0,29:0},'cash_by_day':{28:81.0,29:0.0},'total_cash':81.0},
    'startup_fallback_days':[],'pending_animal_units':{},'conditional_prior_product_sales':True}
ids={n:sha(HERE/(n+'.py')) for n in ('scheduler','checker')};ids['compiler']=sha(HERE/'calendar_compiler.py')
old_cache=route.PlanRouteCache('inline-test',28,private)
new_cache=ns['_r10_route_admission_PlanRouteCache']('inline-test',28,private)
cases=[]
counts={'original_route_calls':0,'inlined_route_calls':0,'scheduler_calls':0,'checker_calls':0}
for name in ('success','cache_hit','startup_reject','anchor_reject'):
    p=deepcopy(base)
    if name=='startup_reject':p['startup_fallback_days']=[29]
    if name=='anchor_reject':p['funding_feed']['stock_by_day']={28:1,29:1}
    before=deepcopy(p)
    outputs=[]
    for function,cache in ((route.route_admission,old_cache),(ns['_r10_route_admission_route_admission'],new_cache)):
        r=function(p,p,current_day=28,observed_private=private,plan_token='inline-test',cache=cache,implementation_ids=ids)
        outputs.append(r)
        counts['scheduler_calls']+=r['scheduler_calls'];counts['checker_calls']+=r['checker_calls']
    counts['original_route_calls']+=1;counts['inlined_route_calls']+=1
    checks[name+'_exact_output_equal']=outputs[0]==outputs[1]
    checks[name+'_input_unchanged']=p==before
    checks[name+'_cache_exact_equal']=old_cache.entries==new_cache.entries
    cases.append({'name':name,'result':outputs[0]})
checks['success_reached_complete_solver_path']=cases[0]['result']['labor_feasible_after_routes'] and cases[0]['result']['checker_calls']==1
checks['cache_hit_avoids_both_solvers']=cases[1]['result']['cache_hits']==1 and cases[1]['result']['scheduler_calls']==0
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
report={'created_utc':stamp,'checks':checks,'check_count':len(checks),'passed':sum(checks.values()),'all_passed':all(checks.values()),
    'source_sha256':{n:sha(HERE/n) for n in ('inline_modules.py','route_admission.py','test_inline_route.py')},
    'inline_metadata':metadata,'cases':cases,'counts':counts,
    'scope':{'pure_definition_exec_only':True,'candidate_calls':0,'official_calls':0,'new_complete_matches':0,'calendar_calls':24}}
path=HERE/('inline_route_tests_'+stamp+'.json');path.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
print(json.dumps({'path':str(path),'checks':len(checks),'passed':sum(checks.values()),'failed':[k for k,v in checks.items() if not v],'counts':counts},ensure_ascii=False))
assert all(checks.values())
