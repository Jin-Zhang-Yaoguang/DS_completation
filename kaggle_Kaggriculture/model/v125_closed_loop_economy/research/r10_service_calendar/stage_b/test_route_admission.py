"""独立准入层纯控制：不导入候选，不调用官方引擎。"""
from pathlib import Path
from copy import deepcopy
from collections import Counter
from datetime import datetime, timezone
import ast
import hashlib
import json
import calendar_compiler as compiler
import route_admission as admission
import scheduler
import checker

HERE = Path(__file__).resolve().parent
MODEL = next(p for p in HERE.parents if p.name == 'v125_closed_loop_economy')
PARENT = MODEL / 'candidates/V125-R9/main.py'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(PARENT) == compiler.PARENT_SOURCE_SHA256
ids = {name: sha(HERE / (name + '.py')) for name in ('scheduler', 'checker')}
ids['compiler'] = sha(HERE / 'calendar_compiler.py')
node = next(n for n in ast.parse(PARENT.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'labor_schedule')
fib, a, b = [], 1, 1
for _ in range(30):
    fib.append(a); a, b = b, a + b
ns = {'PARAMS': {'max_hands': 12}, 'FIB': fib}
exec(compile(ast.Module(body=[node], type_ignores=[]), 'isolated_frozen_r9_labor', 'exec'), ns)
checks, cases = {}, []
counts = Counter()


def enrich(t, today, hour, pos):
    counts['calendar_calls'] += 1
    return compiler.project_calendar_with_services(t, today, hour, pos,
        {'kind': 'artificial_visible_asset_control', 'not_natural_episode': True})


def make_portfolio(cals, today, private, buffer=0, sales=True, startup=None):
    aggregate = admission.aggregate_calendars(cals)
    obs = {'day': today, 'hour': 7, 'player': 0, 'farms': [{'hands': [], 'hires_today': 0}]}
    counts['isolated_legacy_labor_calls'] += 1
    labor = ns['labor_schedule'](obs, aggregate['work'])
    req = {d: aggregate['feed'].get(d, 0) for d in range(today, 30)}
    req[today] += buffer
    held = admission.inventory_totals(private).get('WHEAT', 0)
    buys, stocks, costs = {}, {}, {}
    for d in range(today, 30):
        qty = max(0, req[d] - held)
        held += qty - req[d]
        buys[d], stocks[d], costs[d] = qty, held, 27.0 * qty
    return {'calendars': deepcopy(cals), 'coverage_asset_ids': [c['asset_id'] for c in cals],
        'legacy_aggregate': aggregate, 'workload': deepcopy(aggregate['work']), 'labor': labor,
        'funding_requirements': req,
        'funding_feed': {'buys_by_day': buys, 'stock_by_day': stocks, 'cash_by_day': costs, 'total_cash': sum(costs.values())},
        'startup_fallback_days': list(startup or []), 'pending_animal_units': {},
        'conditional_prior_product_sales': sales}


def run_case(name, base, trial, today, private, cache=None, schedule=None, check=None, token='test-plan'):
    before = deepcopy((base, trial, private))
    cache_before = deepcopy(cache.entries) if cache else None
    counts['route_calls'] += 1
    result = admission.route_admission(base, trial, current_day=today, observed_private=private,
        plan_token=token, cache=cache, schedule=schedule, check=check, implementation_ids=ids)
    counts['scheduler_calls'] += result['scheduler_calls']; counts['checker_calls'] += result['checker_calls']
    unchanged = before == (base, trial, private)
    checks[name + '_inputs_unchanged'] = unchanged
    if not result['labor_feasible_after_routes'] and cache is not None:
        checks[name + '_failure_cache_unchanged'] = cache_before == cache.entries
    cases.append({'name': name, 'result': result})
    return result


empty = {'shed': {}, 'inventories': [{}], 'seeds': {}}
positions = [(x,y) for x in range(3) for y in range(4)] + [(9-x,9-y) for x in range(3) for y in range(4)]
melons = [enrich({'kind': 'PLANT', 'crop': 'MELON', 'planted_day': 18, 'yield_units': 1,
    'consecutive_unwatered': 0, 'watered_today': True, 'fertilized_until_day': -1, 'max_lifespan_step': 744},
    28, 7, pos) for pos in positions]
portfolio = make_portfolio(melons, 28, empty, buffer=3)
cache = admission.PlanRouteCache('test-plan', 28, empty)
r = run_case('terminal_24_melon_route', portfolio, portfolio, 28, empty, cache)
checks['real_future_route_rescues_336_vs_285'] = r['labor_feasible_after_routes'] and r['route_feasibility_by_day'] == {29: True} and portfolio['workload'][29] == 336 and portfolio['labor']['capacity_by_day'][29] == 285
checks['original_hire_376_and_cash_unchanged'] = r['legacy_fields_unchanged']['labor'] == portfolio['labor'] and r['day_evidence'][0]['conditional_result']['hire_cost'] == 376
checks['buffer_occupies_start_and_terminal'] = r['day_evidence'][0]['start_shed']['WHEAT'] == 3 and r['day_evidence'][0]['conditional_result']['terminal_shed']['WHEAT'] >= 3
checks['full_services_72_delivered_48_melon'] = r['day_evidence'][0]['conditional_result']['completed_service_count'] == 72 and r['day_evidence'][0]['conditional_result']['delivered_goods']['MELON'] == 48
r = run_case('same_plan_cache_hit', portfolio, portfolio, 28, empty, cache)
checks['cache_hit_no_solver_calls'] = r['cache_hits'] == 1 and r['scheduler_calls'] == r['checker_calls'] == 0
r = run_case('different_plan_cache_refused', portfolio, portfolio, 28, empty, cache, token='other-plan')
checks['context_mismatch_refused'] = r['reason'] == 'CACHE_CONTEXT_MISMATCH'
changed = deepcopy(portfolio); changed['conditional_prior_product_sales'] = False
r = run_case('changed_conditions_not_cached', changed, changed, 28, empty, cache)
checks['complete_problem_condition_in_cache_key'] = r['scheduler_calls'] == 1 and r['cache_hits'] == 0

small = make_portfolio([melons[0]], 28, empty)
r = run_case('legacy_feasible_no_new_solver', small, small, 28, empty)
checks['original_feasible_not_recomputed'] = r['status'] == 'LEGACY_FEASIBLE_UNCHANGED' and r['scheduler_calls'] == 0

for name, mutate, reason in [
    ('fake_current_anchor', lambda p: [p['funding_feed']['stock_by_day'].__setitem__(d, p['funding_feed']['stock_by_day'][d]+1) for d in (28,29)], 'FUNDING_STOCK_IDENTITY:d28'),
    ('fake_future_stock', lambda p: p['funding_feed']['stock_by_day'].__setitem__(29, 1), 'FUNDING_STOCK_IDENTITY:d29'),
    ('future_extra_requirement', lambda p: p['funding_requirements'].__setitem__(29, 1), 'FUTURE_REQUIREMENTS_NOT_COMPLETE_FEED:d29'),
    ('wrong_legacy_cost', lambda p: (p['labor']['cash_by_day'].__setitem__(29, 232), p['labor'].__setitem__('total_cost',232)), 'LEGACY_FAILED_DAY_NOT_12_HAND_COST_376'),
    ('fake_small_capacity', lambda p: p['labor']['capacity_by_day'].__setitem__(29, 280), 'LEGACY_FAILED_DAY_NOT_MAX_HAND_CAPACITY'),
    ('lost_asset_manifest', lambda p: p['coverage_asset_ids'].pop(), 'COVERAGE_ASSET_MISMATCH'),
    ('work_mismatch', lambda p: p['workload'].__setitem__(29, 337), 'WORKLOAD_COVERAGE'),
    ('startup_unknown_day', lambda p: p['startup_fallback_days'].append(29), 'UNSUPPORTED:UNSUPPORTED_STARTUP_FRONTIER'),
]:
    bad = deepcopy(portfolio); mutate(bad)
    rr = run_case(name, bad, bad, 28, empty, cache)
    checks[name + '_rejected'] = not rr['labor_feasible_after_routes'] and reason in str(rr['reason'])

removed = make_portfolio(melons[:-1], 28, empty, buffer=3)
r = run_case('removed_baseline_asset', portfolio, removed, 28, empty, cache)
checks['baseline_retained'] = r['reason'] == 'TRIAL_REMOVED_BASELINE_ASSET'
modified = deepcopy(portfolio); modified['calendars'][0]['conditional'].append({'kind':'changed_origin'})
r = run_case('changed_baseline_calendar', portfolio, modified, 28, empty, cache)
checks['baseline_calendar_immutable'] = r['reason'] == 'TRIAL_CHANGED_BASELINE_CALENDAR'

# 64 个外围草莓：第一未来日水证可行，下一采收日构造失败；整次 trial 不提交前一日缓存。
straw = [enrich({'kind':'PLANT','crop':'STRAWBERRY','planted_day':0,'yield_units':0,
    'consecutive_unwatered':0,'watered_today':False,'fertilized_until_day':-1,'max_lifespan_step':-1},8,7,(x,y))
    for y in range(10) for x in range(10) if min(x,y,9-x,9-y)<=1]
multi = make_portfolio(straw,8,empty)
cache_multi = admission.PlanRouteCache('test-plan',8,empty)
r = run_case('multi_day_failure_rolls_back', multi, multi,8,empty,cache_multi)
checks['no_partial_route_commit'] = not r['labor_feasible_after_routes'] and r['failed_day']==10 and not r['route_feasibility_by_day'] and not cache_multi.entries and r['scheduler_calls']==2

# 当前劳动不足不调用未来 solver，也不将总空闲转换成可拼接劳动。
water_now = [enrich({'kind':'PLANT','crop':'MELON','planted_day':0,'yield_units':1,
    'consecutive_unwatered':1,'watered_today':False,'fertilized_until_day':-1,'max_lifespan_step':312},0,22,(x,y))
    for y in range(10) for x in range(10)]
now = make_portfolio(water_now,0,empty)
r = run_case('current_failure_unchanged', now,now,0,empty)
checks['current_fail_no_future_attempt'] = r['reason']=='CURRENT_DAY_FAILURE_UNCHANGED' and r['scheduler_calls']==0

# 粮食来源与占仓，用一个完整牛日历核对；成本27是人工条件价，不称真实报价。
cow = enrich({'kind':'PASTURE','animal':'COW','placed_day':0,'yield_units':0,'fed_today':False,
    'cared_today':False,'fertilizer_available':False,'pending_care_bonus':0,'consecutive_unfed':0},0,7,(3,4))
private = {'shed':{'WHEAT':20,'FERTILIZER':2,'SHEEP':1,'MILK':5},'inventories':[{'FERTILIZER':1,'GOOSE':1}], 'seeds':{}}
p = make_portfolio([cow],0,private,buffer=3)
p['pending_animal_units']={'COW':1}
bound = admission.bind_day_materials(p,0,8,private)
checks['buffer_from_requirements_minus_full_feed'] = bound['buffer_debit']==3
checks['wheat_funding_source_formula'] = bound['start_shed']['WHEAT']==p['funding_feed']['stock_by_day'][7]+3 and bound['reserved_shed']['WHEAT']==p['funding_feed']['stock_by_day'][8]+3
checks['fert_actual_plus_prior_goods'] = bound['start_shed']['FERTILIZER']==10
checks['unsold_animals_and_commits_occupy_capacity'] = all(bound['start_shed'][a]==1 and bound['reserved_shed'][a]==1 for a in ('COW','SHEEP','GOOSE'))
checks['sale_condition_does_not_add_cash'] = 'MILK' not in bound['start_shed'] and next(x for x in bound['conditional'] if x['kind']=='conditional_prior_delivery_and_sale')['sales_cash_added_by_route_module']==0
p['conditional_prior_product_sales']=False
b2 = admission.bind_day_materials(p,0,8,private)
checks['no_sale_condition_carries_current_milk'] = b2['start_shed']['MILK']==5
b3 = admission.bind_day_materials(p,0,15,private)
checks['no_free_fert_capacity_reset'] = b3['start_shed']['FERTILIZER']==17
p['conditional_prior_product_sales']=True
checks['fert_cap_has_quantity_source'] = admission.bind_day_materials(p,0,15,private)['start_shed']['FERTILIZER']==12
negative = deepcopy(p); negative['funding_requirements'][0]=0
try: admission.validate_portfolio(negative,0,private); passed=False
except admission.BindingError as e: passed=str(e)=='NEGATIVE_BUFFER_DEBIT'
checks['negative_buffer_rejected']=passed

# 先前已知不可行首水不能靠未来 conditional bridge 恢复健康。
impossible = enrich({'kind':'PLANT','crop':'WHEAT','planted_day':0,'yield_units':1,
    'consecutive_unwatered':1,'watered_today':False,'fertilized_until_day':-1,'max_lifespan_step':120},0,24,(3,4))
pbad = make_portfolio([impossible],0,empty,startup=[0])
try: admission.bind_day_materials(pbad,0,2,empty); passed=False
except admission.BindingError as e: passed='KNOWN_IMPOSSIBLE_CALENDAR_HISTORY' in str(e)
checks['known_impossible_history_not_recovered']=passed
normal = make_portfolio([cow],0,private,startup=[0])
checks['unknown_startup_only_that_day'] = admission.bind_day_materials(normal,0,8,private)['planned_wheat_buy']['qty']>=0

# 源麦大仓占位仍要让 h0 原采购整笔落地；不能先借 SELL 或新产麦跳过购买。
over = {'shed':{'SHEEP':98}, 'inventories':[{}], 'seeds':{}}
overp = make_portfolio(melons,28,over,buffer=3)
r = run_case('carry_capacity_not_erased',overp,overp,28,over)
checks['physical_carry_over100_rejected'] = not r['labor_feasible_after_routes'] and 'START_SHED_OVER_CAPACITY' in r['reason']

# 末预留核的是实际仓内麦，不接受 checker 裸 valid 或背包物量代替。
def altered_terminal(problem, certificate):
    actual = checker.check_day(problem,certificate)
    if actual['valid']:
        actual['stats']['terminal_shed']['WHEAT']=0
        actual['stats']['terminal_inventories']['0']={'WHEAT':3}
    return actual
r=run_case('ending_grain_must_be_shed',portfolio,portfolio,28,empty,check=altered_terminal)
checks['backpack_not_terminal_funding_source'] = r['reason']=='ENDING_WHEAT_RESERVED_SOURCE_SHORTFALL'

stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
report={'created_utc':stamp,'counts':dict(counts),'check_count':len(checks),'passed':sum(checks.values()),
    'all_passed':all(checks.values()),'checks':checks,'cases':cases,
    'source_sha256':{n:sha(HERE/n) for n in ('route_admission.py','test_route_admission.py','calendar_compiler.py','scheduler.py','checker.py')},
    'scope':{'candidate_calls':0,'official_calls':0,'new_complete_matches':0,
        'synthetic_guard_injections':['ending_grain_must_be_shed'],
        'prices':'synthetic fixed27 for funding formula only',
        'fixture_boundaries':'human-constructed visible asset states; no claim of natural whole-game reachability'}}
path=HERE/('route_admission_tests_'+stamp+'.json');path.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
print(json.dumps({'path':str(path),'checks':len(checks),'passed':sum(checks.values()),'failures':[k for k,v in checks.items() if not v], 'counts':dict(counts)},ensure_ascii=False))
assert all(checks.values())
