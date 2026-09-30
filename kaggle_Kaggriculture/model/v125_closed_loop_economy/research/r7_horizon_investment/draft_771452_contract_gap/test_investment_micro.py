#!/usr/bin/env python3
"""R7共享预算与真实市场启动微测，不使用新Replay或完整比赛。"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import hashlib
import json
import sys
import ast

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'r4_contract_design'))
import test_microcases as common
engine=common.scaffold.engine
checks={}; cases={}; runs=[]

def load(path=None):
    path=path or HERE/'main.py'
    spec=importlib.util.spec_from_file_location('investment_'+hashlib.sha256(path.read_bytes()).hexdigest()[:8],path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

def clean(seat=0,day=0,hour=0,cash=3000,sites=None):
    e=common.empty_env(seat,day,hour)
    f=e.state[0].observation.farms[seat]
    f['farmer']=[4,4];f['money']=cash;f['unlocked_quadrants']=['NW']
    f['tiles']=[[None if x<5 and y<5 and (sites is None or (x,y) in sites) else 'LOCKED' for x in range(10)]for y in range(10)]
    e.state[0].observation.town['unlocked_shops']=[]
    e.state[0].observation.market=engine.RULES._new_market();engine.RULES._refresh_prices(e.state[0].observation.market)
    for s in e.state:
        s.observation.market=e.state[0].observation.market
        s.observation.town=e.state[0].observation.town
    return e

def plan(e,m=None,st=None,seat=0):
    m=m or load();o=engine.observed(e,seat);st=st or m.new_state(o);p=m.economic_plan(o,st)
    return m,o,st,p

def safe(x):
    if isinstance(x,dict):return {str(k):safe(v) for k,v in x.items()}
    if isinstance(x,(tuple,list,set)):return [safe(v)for v in x]
    return x

# 首版已复现的纯函数错误保持为负控制，不写入首版源码。
old=load(HERE/'first_draft_cd32'/'main.py')
for label,mod in [('old',old),('new',load())]:
    e=clean(cash=30);m,o,st,p=plan(e,mod)
    cases[label+'_low_cash']={'expert':st['expert'],'accepted':[(q['item'],q['fixed_cash'])for q in p['admitted_investments']]}
checks['old_router_negative_control']=not cases['old_low_cash']['accepted']
checks['new_router_chooses_feasible_cheap']=bool(cases['new_low_cash']['accepted']) and cases['new_low_cash']['expert']=='balanced'

m=load();e=clean(day=0,cash=6000,sites={(4,4)})
o=engine.observed(e,0);q=m.investment_quote(o,'COW',(4,4),m.dated_market_model(o))
cases['new_animal_empty_site_quote']=q
checks['build_buy_pick_place_clock']=q['start_step_model']==3
checks['transport_work_included']=q['setup_work'][0]>=3
f=e.state[0].observation.farms[0];f['tiles'][4][4]={'kind':'PASTURE'}
o=engine.observed(e,0);q=m.investment_quote(o,'COW',(4,4),m.dated_market_model(o))
checks['ready_building_buy_pick_place_clock']=q['start_step_model']==2 and q['setup_work'][0]>=2
f['tiles'][4][4]={'kind':'COOP'};o=engine.observed(e,0)
checks['cannot_rebuild_incompatible_occupied_structure']=m.investment_quote(o,'COW',(4,4),m.dated_market_model(o)) is None

for label,mod in [('old',load(HERE/'first_draft_cd32'/'main.py')),('new',load())]:
    e=clean(day=27,hour=20,cash=100,sites={(4,4)});mod.PARAMS['router']='balanced'
    m,o,st,p=plan(e,mod);tasks=m.make_tasks(o,st,p);orders=m.market_orders(o,st,p,tasks,[['PASS']])
    cases[label+'_late_seed']={'orders':orders,'accepted':p['admitted_investments']}
checks['old_late_seed_conflict_negative_control']=any(a[0]=='BUY_SEED'for a in cases['old_late_seed']['orders'])
checks['new_late_seed_purchase_blocked']=not any(a[0]=='BUY_SEED'for a in cases['new_late_seed']['orders'])

for label,stock in [('no_stock',0),('own_stock',100)]:
    e=clean(cash=6000,sites={(4,4)});e.state[0].observation.private['shed']={'COW':1,'WHEAT':stock}
    e.state[0].observation.farms[0]['tiles'][4][4]={'kind':'PASTURE'}
    m,o,st,p=plan(e)
    cases['transit_'+label]=p['existing_obligations']
    checks['transit_future_feed_'+label]=sum(n for d,n in p['existing_obligations']['feed'].items()if d>0)>0
    checks['transit_future_labor_'+label]=sum(n for d,n in p['existing_obligations']['work'].items()if d>0)>0
    checks['transit_blocks_new_animals_'+label]=not p['animal_purchases']
checks['own_wheat_reduces_actual_cash_need']=cases['transit_own_stock']['feed_cash']==0<cases['transit_no_stock']['feed_cash']
checks['own_wheat_not_economically_free']=cases['transit_own_stock']['feed_opportunity']>0

m=load();e=clean();o=engine.observed(e,0);model=m.dated_market_model(o)
requirements={0:3,1:2};ledger=m.feed_ledger(o,model,requirements,2)
expected=sum(m.price('WHEAT',model['inventories'][d]['WHEAT']-k-1,o['market'].get('params'))for d,n in {0:1,1:2}.items()for k in range(n))
checks['feed_postbuy_unit_price']=ledger['cash']==expected and ledger['owned_used']==2 and ledger['units']==5
low=m.investment_quote(o,'COW',(4,4),model)
for d in model['inventories']:model['inventories'][d]['WHEAT']=-100000;model['prices'][d]['WHEAT']=m.price('WHEAT',-100000,o['market'].get('params'))
high=m.investment_quote(o,'COW',(4,4),model)
checks['feed_price_changes_net']=high['net_before_hiring_model']<0<low['net_before_hiring_model']
cases['feed_price_control']={'low':low['net_before_hiring_model'],'high':high['net_before_hiring_model']}

# 当天已成熟现貨次日进入供给模型，不能永远漏掉。
e=clean(day=12,sites={(4,4)});f=e.state[0].observation.farms[0]
f['tiles'][4][4]=engine.RULES._new_animal('COW',0);f['tiles'][4][4].update(yield_units=3,fertilizer_available=True,fed_today=True,cared_today=True)
m=load();o=engine.observed(e,0);md=m.dated_market_model(o)
checks['current_goods_enter_next_day']=md['inventories'][13]['MILK']==o['market']['inventory']['MILK']-1+3 and md['inventories'][13]['FERTILIZER']==o['market']['inventory']['FERTILIZER']+1

# 真正存续的PLANT/BUILD合同在高层先占位置和投入。
for kind in ['PLANT','BUILD_PASTURE']:
    e=clean(cash=6000,sites={(4,4),(3,4)});m=load();o=engine.observed(e,0);st=m.new_state(o)
    if kind=='PLANT':e.state[0].observation.private['seeds']={'TOMATO':1};o=engine.observed(e,0)
    else:e.state[0].observation.private['shed']={'COW':1};o=engine.observed(e,0)
    st['contracts']={0:{'target':(4,4),'stages':[{'op':['PLANT','TOMATO']if kind=='PLANT'else[kind]}]}}
    p=m.economic_plan(o,st)
    checks[kind+'_contract_reserved']=(4,4)in p['reserved_animal_sites'] and not any(tuple(q['position'])==(4,4) for q in p['admitted_investments'])
    if kind=='BUILD_PASTURE':
        checks['existing_transit_build_not_duplicated']=len(p['build_permits'])==1 and p['existing_obligations']['transit_project_count']==1 and p['existing_obligations']['committed_fixed_cash']==0

# 终局不产生新动物/种子许可，诊断仍有最后一帧。
e=clean(day=29,hour=22,cash=100000);m,o,st,p=plan(e)
checks['terminal_no_unrealizable_investment']=not p['admitted_investments'] and not p['animal_purchases'] and not p['seed_purchases']
m._STATES[0]=st;json.dumps(m.diagnostics(),allow_nan=False)
checks['finite_diagnostics_last_step']=st['investment_receipts'][-1]['step']==718

# 共享现金扣账与扩地：保留旧占用门槛，未真实解锁的地不得获任务。
for cash in [0,30,3000,10000]:
    e=clean(day=5,cash=cash);m,o,st,p=plan(e)
    reserved=p['existing_obligations']['reserved_cash']+sum(q['cash_reserved_model']for q in p['admitted_investments'])+p['land_cash']
    checks['shared_cash_'+str(cash)]=reserved<=cash+1e-6
    checks['unique_sites_'+str(cash)]=len({tuple(q['position'])for q in p['admitted_investments']})==len(p['admitted_investments'])

# HIRE实际提交/成交；hour7不能借h8不再提供的第11/12名工人。
for seat in [0,1]:
    e=clean(seat,hour=7,cash=10000)
    f=e.state[0].observation.farms[seat]
    f['unlocked_quadrants']=['NW','NE','SW','SE'];f['tiles']=[[None for x in range(10)]for y in range(10)]
    m=load();o=engine.observed(e,seat);st=m.new_state(o);p=m.economic_plan(o,st);tasks=m.make_tasks(o,st,p)
    orders=m.market_orders(o,st,p,tasks,[['PASS']])
    hires=sum(a[0]=='HIRE'for a in orders)
    pair=[deepcopy(engine.PASS),deepcopy(engine.PASS)];pair[seat]={'farmer':['PASS'],'hands':[],'market':orders}
    engine.official_step(e,pair);after=engine.observed(e,seat)
    cases['hire_h7_s'+str(seat)]={'target':p['hire_target_today'],'orders':orders,'hands_after':len(after['farms'][seat]['hands']),'work':p['planned_work'],'capacity':p['labor_plan']['capacity_by_day']}
    checks['hire_h7_real_commit_s'+str(seat)]=hires==p['hire_target_today']==len(after['farms'][seat]['hands'])<=10 and len(orders)<=10
    checks['hire_h7_admitted_capacity_s'+str(seat)]=p['planned_work'].get(0,0)<=16+hires*15
    m2=load();p2=m2.labor_schedule(after,{0:1000})
    checks['h8_no_phantom_workers_s'+str(seat)]=not p2['feasible'] and p2['hire_target_today']==len(after['farms'][seat]['hands'])

# 空地→建设→真实买入→领取→投放，人工状态连续使用官方解释器。
for seat in [0,1]:
    e=clean(seat,cash=6000,sites={(4,4)});m=load();m.PARAMS['router']='dairy'
    result,m=common.run(e,seat,9,'first_animal_bootstrap',module=m);runs.append(result)
    orders=[(r['step'],a)for r in result['rows']for a in r['applied']['market']]
    actions=[(r['step'],r['applied']['farmer'])for r in result['rows']]
    steps={op:next((s for s,a in actions if a[0]==op),None)for op in ['BUILD_PASTURE','PICKUP','PLACE']}
    buy=next((s for s,a in orders if a[0]=='BUY_ANIMAL'),None)
    final=result['final']['farms'][seat]['tiles'][4][4]
    checks['first_animal_bootstrap_s'+str(seat)]=final.get('animal')=='COW' and steps['BUILD_PASTURE'] is not None and buy is not None and steps['BUILD_PASTURE']<buy<steps['PICKUP']<steps['PLACE']
    checks['first_animal_no_borrowed_future_purchase_s'+str(seat)]=buy is not None and all(not any(a[0]=='BUY_ANIMAL'for a in r['applied']['market'])for r in result['rows']if r['step']<buy)
    checks['first_animal_confirmed_s'+str(seat)]=m._STATES[seat]['metrics']['purchase_BUY_ANIMAL_confirmed']>=1 if 'purchase_BUY_ANIMAL_confirmed'in m._STATES[seat]['metrics'] else any(x.get('animal')=='COW'for row in result['final']['farms'][seat]['tiles']for x in row if isinstance(x,dict))

# 无融资的新土地付款控制；本帧看见的所有任务仍须属于实际解锁地。
for seat in [0,1]:
    e=clean(seat,day=5,hour=8,cash=10000);f=e.state[0].observation.farms[seat]
    positions=[(x,y)for y in range(5)for x in range(5)][:17]
    for x,y in positions:
        t=engine.RULES._new_plant('CARROT',2,120);t.update(watered_today=True,yield_units=3);f['tiles'][y][x]=t
    m,o,st,p=plan(e,seat=seat);tasks=m.make_tasks(o,st,p);orders=m.market_orders(o,st,p,tasks,[['PASS']])
    checks['land_budget_permitted_s'+str(seat)]=p['buy_land'] and p['land_cash']==1000 and any(a[0]=='BUY_LAND'for a in orders)
    checks['no_locked_land_tasks_s'+str(seat)]=all(o['farms'][seat]['tiles'][t['pos'][1]][t['pos'][0]]!='LOCKED'for t in tasks)
    pair=[deepcopy(engine.PASS),deepcopy(engine.PASS)];pair[seat]={'farmer':['PASS'],'hands':[],'market':orders};engine.official_step(e,pair)
    checks['land_real_commit_s'+str(seat)]=len(engine.observed(e,seat)['farms'][seat]['unlocked_quadrants'])==2

oldtree=ast.parse((HERE/'parent_r6.py').read_text());newtree=ast.parse((HERE/'main.py').read_text())
of={n.name:ast.dump(n,include_attributes=False)for n in oldtree.body if isinstance(n,ast.FunctionDef)};nf={n.name:ast.dump(n,include_attributes=False)for n in newtree.body if isinstance(n,ast.FunctionDef)}
changed={k for k in of if of[k]!=nf[k]}
checks['only_allowed_old_functions_changed']=changed=={'economic_plan','make_tasks','market_orders','diagnostics'}
source_sha=hashlib.sha256((HERE/'main.py').read_bytes()).hexdigest()
result={'source_sha256':source_sha,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'checks':checks,'passed':sum(checks.values()),'total':len(checks),'cases':safe(cases),'runs':safe(runs),'changed_functions':sorted(changed)}
name='investment_micro_'+source_sha[:12]+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'
(HERE/name).write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
print(json.dumps({'result':name,'passed':result['passed'],'total':len(checks),'failed':[k for k,v in checks.items()if not v]},ensure_ascii=False))
