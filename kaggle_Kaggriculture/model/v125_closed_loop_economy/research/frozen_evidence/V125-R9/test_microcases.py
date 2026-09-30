#!/usr/bin/env python3
"""R9 资金前缀微测：人工可见状态与既有官方短控制，无完整比赛。"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import ast, hashlib, importlib.util, json, sys, time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'r4_contract_design'))
import test_microcases as common
engine = common.scaffold.engine
checks, details, runs = {}, {}, []


def load(parent=False):
    p = HERE / ('parent_r8.py' if parent else 'main.py')
    spec = importlib.util.spec_from_file_location('r9_control_' + str(parent), p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def clean(seat=0, day=0, hour=0, cash=3000, sites=None):
    e = common.empty_env(seat, day, hour)
    f = e.state[0].observation.farms[seat]
    f['farmer'], f['money'], f['unlocked_quadrants'] = [4, 4], cash, ['NW']
    f['tiles'] = [[None if x < 5 and y < 5 and (sites is None or (x,y) in sites) else 'LOCKED' for x in range(10)] for y in range(10)]
    for s in e.state: s.observation.town['unlocked_shops'] = []
    return e


m = load()
bad = m.cash_prefix_scan(50, 0, {1:60}, {2:100})
good = m.cash_prefix_scan(50, 0, {2:60}, {1:100})
checks['early_deficit_not_paid_by_late_credit'] = not bad['feasible'] and bad['first_negative_day'] == 1 and bad['before_credit'][1] == -10
checks['earlier_credit_can_pay_later_expense'] = good['feasible'] and good['before_credit'][2] == 90
checks['same_day_wage_before_sale_credit'] = not m.cash_prefix_scan(50, 0, {1:60}, {1:100})['feasible']
checks['current_day_unsettled_sale_ignored'] = not m.cash_prefix_scan(0, 0, {0:1}, {0:100})['feasible']
checks['zero_credit_same_expenses_full_reserve_pass'] = m.cash_prefix_scan(60, 0, {1:20,29:40}, {})['feasible']
checks['zero_credit_same_expenses_full_reserve_fail'] = not m.cash_prefix_scan(59, 0, {1:20,29:40}, {})['feasible']
checks['current_additional_spend_is_min_prefix_not_final'] = good['additional_current_spend'] == 50

baseline = m.cash_prefix_scan(10, 0, {1:20}, {})
checks['existing_deficit_zero_cash_reuse'] = m.prefix_admission(baseline, deepcopy(baseline), 0) == 'EXISTING_SHORTFALL_ZERO_NEW_CASH_REUSE'
checks['existing_deficit_positive_cash_no_reuse'] = m.prefix_admission(baseline, deepcopy(baseline), 1) is None
worse = m.cash_prefix_scan(10, 0, {1:21}, {})
checks['zero_nominal_cash_but_worse_prefix_rejected'] = m.prefix_admission(baseline, worse, 0) is None

# 真实在田与当前库存的资格边界；模型日历单独做末日控制。
e = clean(day=10, sites={(4,4),(3,4)}); f = e.state[0].observation.farms[0]
f['tiles'][4][4] = engine.RULES._new_animal('COW', 0)
e.state[0].observation.private['shed'] = {'SHEEP':2,'MILK':5,'WHEAT':8,'FERTILIZER':3}
e.state[0].observation.private['seeds'] = {'MELON':2}
o = engine.observed(e,0); model = m.dated_market_model(o)
batches, sources = m.credit_batches_from_field(o,model)
checks['credit_only_real_own_field_position'] = sources == [[4,4]]
checks['in_transit_seed_and_held_products_no_extra_credit'] = all(p == 'MILK' for _,p in batches)
checks['wheat_fertilizer_excluded'] = not any(p in ('WHEAT','FERTILIZER') for _,p in batches)
special = {'calendars':[(0,(4,4),{'goods':{28:{'MILK':2,'WHEAT':10,'FERTILIZER':8},29:{'MILK':99}}}), (1,(3,4),{'goods':{28:{'MILK':1000}}})]}
end, _ = m.credit_batches_from_field({**o,'day':28}, special)
checks['day28_goods_credit_day29_and_day29_goods_removed'] = end == {(29,'MILK'):2}
checks['current_day_credit_not_backfilled'] = m.credit_batches_from_field({**o,'day':29}, special)[0] == {}

# 同批后端价不重复加量，试加供给不写原model；全组旧收入不能借两次。
o = engine.observed(clean(),0); model = m.dated_market_model(o)
batches = {(2,'MILK'):10}; ceiling = m.price_credit_batches(o,model,batches)
checks['postbatch_price_times_aggregate_quantity'] = ceiling[(2,'MILK')] == 10*m.price('MILK',model['inventories'][2]['MILK'],o['market'].get('params'))
original = deepcopy(model); trial_model = m.clone_funding_model(model)
m.apply_project_supply(o,trial_model,{'goods':{1:{'MILK':1000}},'feed':{}})
lower = m.price_credit_batches(o,trial_model,batches,ceiling)
checks['new_supply_lowers_old_income_credit'] = lower[(2,'MILK')] < ceiling[(2,'MILK')]
checks['trial_model_has_no_side_effect_on_original'] = model == original
optimistic = m.clone_funding_model(model); optimistic['inventories'][2]['MILK'] -= 10000
checks['credit_cannot_exceed_initial_ceiling'] = m.price_credit_batches(o,optimistic,batches,ceiling) == ceiling
checks['new_project_goods_not_added_to_credit_quantity'] = list(lower) == list(batches)
for index, cal in enumerate([
        {'goods':{},'feed':{}},
        {'goods':{0:{'MILK':3},1:{'MILK':2,'MELON':6},29:{'MILK':20}},'feed':{0:2,1:1,28:3}},
        {'goods':{7:{'CARROT':4},28:{'STRAWBERRY':3}},'feed':{2:5,18:8}},
        {'goods':{d:{'MILK':d % 6,'WOOL':d % 4} for d in range(30)},'feed':{d:2 for d in range(30)}}]):
    prior = deepcopy(model); m.apply_project_supply(o,prior,cal)
    optimized = m.funding_trial_model(o,model,cal)
    checks['optimized_trial_exact_old_inventory_prices_'+str(index)] = optimized == prior
labor = {'cash_by_day':{d:0 for d in range(30)}}
book = m.funding_cash_book(o,model,{},labor,0,batches,ceiling)
checks['shared_credit_counted_once'] = sum(book['credits_by_day'].values()) == sum(ceiling.values())
rejected_trial = m.funding_cash_book(o,trial_model,{},labor,4000,batches,ceiling)
checks['rejected_trial_keeps_original_and_repeat_identical'] = not rejected_trial['feasible'] and model == original and rejected_trial == m.funding_cash_book(o,trial_model,{},labor,4000,batches,ceiling)
low_cash_o = deepcopy(o); low_cash_o['farms'][0]['money'] = 50
cost_labor = {'cash_by_day':{d:(100 if d == 3 else 0) for d in range(30)}}
base_group = m.funding_cash_book(low_cash_o,model,{},cost_labor,0,batches,ceiling)
repriced_group = m.funding_cash_book(low_cash_o,trial_model,{},cost_labor,0,batches,ceiling)
checks['repricing_rechecks_all_existing_group_expenses'] = base_group['feasible'] and not repriced_group['feasible']

# 人工可核查报价：旧在田商品才可贷；多个项目共用一笔160信用，不能每项各借160。
fake = load(); env = clean(cash=100, sites={(0,0),(4,4),(3,4)})
env.state[0].observation.farms[0]['tiles'][0][0] = engine.RULES._new_plant('MELON',0,0)
fo = engine.observed(env,0)
fm = fake.dated_market_model(fo)
fm['calendars'] = [(0,(0,0),{'goods':{0:{'MILK':1}},'work':{},'feed':{}})]
for d in range(30):
    fm['inventories'][d]['MILK'] = 10000
    fm['inventories'][d]['WHEAT'] = 10000
fake.dated_market_model = lambda obs: deepcopy(fm)
def synthetic_quote(obs,item,pos,model,seed_credit=False,already_owned=False,committed=False):
    if item != 'MELON': return None
    return {'item':item,'position':pos,'build_first':False,'start_step_model':obs['step'],
            'first_product_day':3,'calendar':{'goods':{3:{'MELON':20}},'work':{2:1},'feed':{2:5}},
            'fixed_cash':10,'gross_cash_model':5000.,'feed_cost_model':125.,'net_before_hiring_model':4865.,
            'labor':1,'score_before_hiring':4865.,'setup_work':{}}
fake.investment_quote = synthetic_quote
fst = fake.new_state(fo); fp = fake.economic_plan(fo,fst)
details['synthetic_shared_credit'] = {'accepted':len(fp['admitted_investments']),'rejections':fp['rejected_types'],
                                     'funding':fp['funding_book']}
checks['shared_credit_allows_one_not_two_synthetic_projects'] = len(fp['admitted_investments']) == 1 and fp['rejected_types'].get('cash_prefix',0)>0
checks['new_project_future_goods_never_self_finance'] = fp['funding_book']['credit_batches'] == [{'credit_day':1,'product':'MILK','quantity':1,'cash_model':160.0}]
checks['synthetic_prefix_permit_old_full_cash_would_reject'] = fp['admitted_investments'][0]['cash_reserved_model'] > 100
checks['synthetic_source_model_not_mutated_by_rejections'] = fm['inventories'][4]['MELON'] == fake.dated_market_model(fo)['inventories'][4]['MELON']

# 当前原市场提前补货结转；10%只现金约束，不改经济机会成本。
e = clean(); e.state[0].observation.farms[0]['tiles'][4][4] = engine.RULES._new_animal('COW',0)
o = engine.observed(e,0); model = m.dated_market_model(o)
req = {0:1,1:1,2:1,3:1}; fs = m.funding_feed_schedule(o,model,req)
checks['market_prefetch_quantity_preserved'] = fs['buys_by_day'][0] == 4
checks['prefetch_carried_no_double_future_buy'] = sum(fs['buys_by_day'].values()) == 4 and fs['stock_by_day'][3] == 0
checks['current_feed_ten_percent_cash_margin'] = fs['cash_by_day'][0] == m.current_feed_order_estimate(o)['cash_limit']
old_ledger = m.feed_ledger(o,model,req,0)
checks['economic_feed_cost_not_inflated_by_margin'] = old_ledger['opportunity'] < fs['cash_by_day'][0]
owned_ledger = m.feed_ledger(o,model,req,4)
checks['owned_wheat_cash_zero_opportunity_positive'] = owned_ledger['cash'] == 0 and owned_ledger['opportunity'] > 0

# 相同高现金计划，原净值三个分数及执行任务不因资金辅助账而改变。
e = clean(cash=1000000,sites={(4,4)})
o = engine.observed(e,0); parent = load(True); fresh = load()
sp,sn = parent.new_state(o),fresh.new_state(o)
pp,pn = parent.economic_plan(o,sp),fresh.economic_plan(o,sn)
keys = ['item','net_cash_model','score','selection_score','cash_reserved_model','feed_cost_model','hire_cash_model']
checks['same_quote_original_net_and_scores_equal'] = [{k:q[k] for k in keys} for q in pp['admitted_investments']] == [{k:q[k] for k in keys} for q in pn['admitted_investments']]
checks['same_plan_execution_tasks_equal'] = parent.make_tasks(deepcopy(o),deepcopy(sp),deepcopy(pp)) == fresh.make_tasks(deepcopy(o),deepcopy(sp),deepcopy(pp))
checks['one_animal_per_frame'] = sum(q['item'] in m.ANIMALS for q in pn['admitted_investments']) <= 1
json.dumps(sn['investment_receipts'],allow_nan=False)
checks['receipt_json_finite_serializable'] = True

# 原资金路径同源短官方控制：六对、120实际决策，不开完整比赛。
for seat in (0,1):
    for case,d,h,n in [('initial',0,0,12),('care_crossday',10,16,8),('in_transit',3,3,10)]:
        outcomes=[]
        for old in (True,False):
            env=clean(seat,day=d,hour=h,cash=6000)
            if case=='care_crossday':
                env.state[0].observation.farms[seat]['tiles'][4][4]=engine.RULES._new_animal('COW',0)
                env.state[0].observation.farms[seat]['tiles'][4][3]=engine.RULES._new_plant('STRAWBERRY',0,240)
                env.state[seat].observation.private['shed']={'WHEAT':8,'FERTILIZER':3}
                env.state[seat].observation.private['seeds']={'CARROT':2}
            if case=='in_transit': env.state[seat].observation.private['shed']={'SHEEP':1,'WHEAT':10}
            mod=load(old)
            if not old:mod.PARAMS['cash_funding']='full_reserve'
            run,_=common.run(env,seat,n,case+('_R8' if old else '_R9_full_reserve'),module=mod)
            outcomes.append(run);runs.append(run)
        a,b=outcomes
        checks[case+'_full_reserve_actions_s'+str(seat)]=[r['applied'] for r in a['rows']]==[r['applied'] for r in b['rows']]
        checks[case+'_full_reserve_final_s'+str(seat)]=a['final']==b['final']

# 新资金路径短官方动作及h7低现金订单：不凭未成交SELL支付。
for seat in (0,1):
    for case,d,h,cash,n in [('prefix_start',0,0,3000,6),('prefix_h7_cash',1,7,3,2)]:
        env=clean(seat,day=d,hour=h,cash=cash)
        if h==7:
            env.state[0].observation.farms[seat]['tiles'][4][4]=engine.RULES._new_animal('COW',0)
            env.state[seat].observation.private['shed']={'MILK':20}
        mod=load();run,mod=common.run(env,seat,n,case,module=mod);runs.append(run)
        for row in run['rows']:
            act=row['applied'];market=act.get('market',act.get('orders',[]))
            checks[case+'_market_slots_s'+str(seat)+'_'+str(row['step'])]=len(market)<=10
        json.dumps(run['diagnostics'],allow_nan=False)
        checks[case+'_diagnostic_json_s'+str(seat)]=True
        if h==7:
            first=run['rows'][0]['applied']
            details['h7_s'+str(seat)]=first
            checks['h7_does_not_borrow_s'+str(seat)]=not any(x[0] in ('BUY_ANIMAL','BUY_SEED','BUY_PRODUCT','BUY_LAND') for x in first.get('market',[]))

old_tree,new_tree=ast.parse((HERE/'parent_r8.py').read_text()),ast.parse((HERE/'main.py').read_text())
oldf={x.name:x for x in old_tree.body if isinstance(x,ast.FunctionDef)};newf={x.name:x for x in new_tree.body if isinstance(x,ast.FunctionDef)}
changed=[k for k in oldf if ast.dump(oldf[k],include_attributes=False)!=ast.dump(newf[k],include_attributes=False)]
checks['only_original_economic_plan_changed']=changed==['economic_plan']
checks['full_reserve_body_ast_exact_parent']=ast.dump(ast.Module(body=oldf['economic_plan'].body,type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=newf['economic_plan_full_reserve'].body,type_ignores=[]),include_attributes=False)
mod=load();mod.PARAMS['cash_funding']='bad'
try:mod.economic_plan(o,mod.new_state(o));checks['unknown_funding_rejected']=False
except ValueError:checks['unknown_funding_rejected']=True

# 性能仅人工可见状态的纯计划调用；不执行agent/引擎，不作G0资格。
performance=[]
for size in (25,100):
    env=clean(cash=10000)
    if size==100:
        farm=env.state[0].observation.farms[0];farm['tiles']=[[None for _ in range(10)] for _ in range(10)]
        farm['unlocked_quadrants']=['NW','NE','SW','SE']
    po=engine.observed(env,0)
    for attempt in range(2):
        mod=load();st=mod.new_state(po);started=time.perf_counter();pl=mod.economic_plan(po,st)
        performance.append({'empty_tiles':size,'attempt':attempt,'elapsed_ms':(time.perf_counter()-started)*1000,
                            'admitted':len(pl['admitted_investments'])})
details['plan_only_performance']=performance
sha=hashlib.sha256((HERE/'main.py').read_bytes()).hexdigest()
result={'source_sha256':sha,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'checks':checks,'passed':sum(checks.values()),'total':len(checks),'details':details,'changed_original_functions':changed,'runs':runs,'complete_matches':0,'new_replays_opened':False}
out=HERE/('micro_'+sha[:12]+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
print(json.dumps({'result':str(out),'passed':sum(checks.values()),'total':len(checks),'failed':[k for k,v in checks.items() if not v]},ensure_ascii=False))
