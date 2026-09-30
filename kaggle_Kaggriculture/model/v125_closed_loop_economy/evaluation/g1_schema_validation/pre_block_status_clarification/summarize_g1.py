#!/usr/bin/env python3
"""只读汇总冻结运行与机制账本；缺失资格证据时保持 PENDING。"""
from __future__ import annotations
import argparse, collections, copy, gzip, hashlib, json, statistics
from pathlib import Path
from datetime import datetime, timezone

HERE=Path(__file__).resolve().parent
SCHEMA='v125-g1-evidence-summary-v1'
MOVES={'NORTH','SOUTH','EAST','WEST'}
CROPS={'WHEAT':(2,4,0,6),'CARROT':(2,3,0,4),'TOMATO':(8,8,1,4),'STRAWBERRY':(10,10,2,4),'MELON':(10,12,0,6)}
ANIMALS={'COW':'MILK','SHEEP':'WOOL','GOOSE':'EGG'}
RULE_SHA='bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def read(p):return json.loads(Path(p).read_text())
def ratio(n,d):return n/d if d else None
def status(values):return 'FAIL' if 'FAIL' in values else 'PENDING' if 'PENDING' in values else 'PASS'
def metric(state,reason,**values):return {'status':state,'reason':reason,**values}
def counter(x):return +collections.Counter(x)
def add(a,b):
    for k,v in b.items():a[k]+=v
def inventory(private,products):
    x=collections.Counter(private['shed'])
    for z in private['inventories']:x.update(z)
    return collections.Counter({k:v for k,v in x.items() if k in products and v})
def ready(tile,day):
    if not isinstance(tile,dict):return collections.Counter()
    c=tile.get('crop');animal=tile.get('animal');r=collections.Counter()
    if c and c in CROPS and day-tile['planted_day']>=CROPS[c][0]:r[c]+=tile.get('yield_units',0)
    if animal:
        r[ANIMALS[animal]]+=tile.get('yield_units',0)
        r['FERTILIZER']+=int(bool(tile.get('fertilizer_available')))
    return +r
def field_ready(board,day):
    x=collections.Counter()
    for row in board:
        for t in row:add(x,ready(t,day))
    return +x

def closing_measurement(game,audit,events,daily,terminal):
    """末日事件账本独立核对开盘/收盘现货，生产量不取守恒残差倒算。"""
    seat=game['candidate_seat'];end=terminal[seat];day=end['day'];prices=end['market']['prices'];products=set(prices)
    opening=next((z['states'][seat] for z in daily if z['states'][seat]['day']==day and z['states'][seat]['hour']==0),None)
    if opening is None:return metric('PENDING','缺少末日开始状态，无法建立独立物料分母')
    board=copy.deepcopy(opening['farms'][seat]['tiles']);start_inv=inventory(opening['private'],products);start_field=field_ready(board,day)
    start=start_inv.copy();start.update(start_field)
    sold=collections.Counter();real_cash=collections.Counter();bought=collections.Counter();used=collections.Counter();made=collections.Counter();destroyed=collections.Counter()
    destroyed_detail=[];errors=[];last=[z for z in events if z['seat']==seat and z['day']==day]
    for z in last:
        kind=z['kind'];pos=z.get('position');x,y=pos if pos else (None,None);t=board[y][x] if pos else None
        if kind=='market':
            if z['op']=='SELL':sold[z['item']]+=z['quantity'];real_cash[z['item']]+=z['price']
            if z['op']=='BUY_PRODUCT':bought[z['item']]+=z['quantity']
        elif kind=='water':
            if not isinstance(t,dict) or t.get('crop')!=z['crop']:
                errors.append({'kind':'WATER_TILE_MISMATCH','step':z['decision_step'],'position':pos});continue
            before=ready(t,day);c=t['crop'];first,maxday,interval,limit=CROPS[c];age=day-t['planted_day']
            if t.get('watered_today'):errors.append({'kind':'DUPLICATE_SUCCESSFUL_WATER','step':z['decision_step'],'position':pos})
            if not interval and (maxday+1)//2<=age<=maxday:
                t['yield_units']=min(limit,t.get('yield_units',0)+(2 if t.get('fertilized_until_day',-1)>=day else 1))
            t['watered_today']=True;add(made,ready(t,day)-before)
        elif kind=='plant':
            c=z['crop'];board[y][x]={'kind':'PLANT','crop':c,'planted_day':day,'yield_units':0 if CROPS[c][2] else 1,'fertilized_until_day':-1,'watered_today':False}
        elif kind=='place_animal':
            board[y][x]={'animal':z['animal'],'placed_day':day,'yield_units':0,'fertilizer_available':False}
        elif kind=='fertilize':
            used[z['item']]+=z['quantity']
            if isinstance(t,dict):t['fertilized_until_day']=max(t.get('fertilized_until_day',-1),day+2)
        elif kind=='feed':used[z['item']]+=z['quantity']
        elif kind=='harvest':
            expected=ready(t,day).get(z['item'],0)
            if expected!=z['quantity']:errors.append({'kind':'HARVEST_READY_MISMATCH','step':z['decision_step'],'position':pos,'item':z['item'],'expected':expected,'actual':z['quantity']})
            if isinstance(t,dict):
                if z['item']=='FERTILIZER':t['fertilizer_available']=False
                elif t.get('crop') and not CROPS[t['crop']][2]:board[y][x]=None
                else:t['yield_units']=0
        elif kind in ('standing_yield_decay','dig_crop','eod_plant_death','eod_animal_escape'):
            before=ready(t,day)
            if kind=='standing_yield_decay' and isinstance(t,dict):
                t['yield_units']=max(0,t.get('yield_units',0)-z['quantity'])
                if z['became_weed']:board[y][x]={'kind':'WEED'}
            else:board[y][x]=None
            lost=before-ready(board[y][x],day);add(destroyed,lost)
            if lost:destroyed_detail.append({'step':z['decision_step'],'kind':kind,'position':pos,'quantity':dict(lost)})
        elif kind in ('manual_drop_overflow','eod_inventory_drop'):
            loss=z['quantity'] if kind=='manual_drop_overflow' else z['discarded']
            loss={k:v for k,v in loss.items() if k in products};add(destroyed,loss)
            if loss:destroyed_detail.append({'step':z['decision_step'],'kind':kind,'quantity':loss})
    end_inv=inventory(end['private'],products);end_field=field_ready(end['farms'][seat]['tiles'],day);left=end_inv.copy();left.update(end_field)
    tracked_field=field_ready(board,day)
    if tracked_field!=end_field:errors.append({'kind':'FINAL_READY_FIELD_MISMATCH','tracked':dict(tracked_field),'observed':dict(end_field)})
    balance={}
    for item in sorted(products):
        z={'opening_inventory':start_inv[item],'opening_mature_field_and_fertilizer':start_field[item],'new_ready_production':made[item],
           'buy_product':bought[item],'real_sell_quantity':sold[item],'feed_or_fertilize_consumption':used[item],
           'ready_destroyed':destroyed[item],'terminal_inventory':end_inv[item],'terminal_mature_field_and_fertilizer':end_field[item]}
        z['residual']=start[item]+made[item]+bought[item]-sold[item]-used[item]-destroyed[item]-left[item];balance[item]=z
    closed=not errors and all(z['residual']==0 for z in balance.values())
    valuation=lambda x:sum(prices[k]*v for k,v in x.items())
    sold_value=valuation(sold);left_value=valuation(left);lost_value=valuation(destroyed);den=sold_value+left_value+lost_value;r=ratio(sold_value,den)
    state='PENDING' if bought or not closed or not den else 'PASS' if r>=.95 else 'FAIL'
    reason='末日真实卖出与残留/已可售销毁按同一终局价格加权'
    if bought:reason+='；末日有BUY_PRODUCT，分母可能受转售放大，待来源分解'
    if not closed:reason+='；末日物料未闭合或事件不完整'
    if not den:reason+='；分母为零'
    return metric(state,reason,day=day,decision_window=[opening['step'],end['step']-1],numerator=sold_value,denominator=den,ratio=r,
                  threshold=.95,real_sale_qty=dict(sold),real_sale_cash=dict(real_cash),real_sale_cash_total=sum(real_cash.values()),
                  final_quote_prices=prices,sold_at_final_quote=sold_value,terminal_remaining_at_final_quote=left_value,
                  ready_destroyed_at_final_quote=lost_value,terminal_inventory_qty=dict(end_inv),terminal_mature_field_and_fertilizer_qty=dict(end_field),
                  final_day_bought=dict(bought),final_day_consumed=dict(used),ready_destroyed_qty=dict(destroyed),ready_destroyed_events=destroyed_detail,
                  independent_material_balance=balance,material_closed=closed,material_errors=errors,
                  formula='Σ(p_end*q_real_SELL_lastday) / Σ[p_end*(q_real_SELL_lastday+q_remaining_end+q_ready_destroyed_lastday)]',
                  no_full_season_cash_or_sales_in_denominator=True)

def actions_metric(game,trace):
    seat=game['candidate_seat'];requested=collections.Counter();unclear=0
    for pair in trace['actions']:
        action=pair[seat]
        for raw in [action.get('farmer',['PASS'])]+action.get('hands',[]):
            if not isinstance(raw,list) or not raw or not isinstance(raw[0],str):unclear+=1;continue
            if raw[0] not in MOVES|{'PASS'}:requested[raw[0]]+=1
    counts=game.get('action_audit',{}).get('unit_counts',[{},{}])[seat]
    den=sum(requested.values())+unclear;invalid=0;covered=0;perop={}
    for op,n in requested.items():
        submitted=counts.get('submitted_'+op,0);changed=counts.get('changed_'+op,0)
        known=max(0,submitted-changed);atomic=counts.get('atomic_plant_blocked_requests',0) if op=='PLANT' else 0
        unknown=max(0,n-submitted-atomic);invalid+=known+atomic;covered+=submitted+atomic
        perop[op]={'raw_requested':n,'observed_after_atomic_filter':submitted,'state_changed':changed,'confirmed_no_change_or_atomic_block':known+atomic,'unattributed':unknown}
    unknown=max(0,den-covered);lo=ratio(invalid,den);hi=ratio(invalid+unknown,den)
    st='PENDING' if not den or unknown else 'PASS' if lo<=.01 else 'FAIL'
    if den and lo>.01:st='FAIL'
    return metric(st,'剔除PASS与四个移动指令；原子播种阻断计无效，不确定请求仍留分母且不当成功',
                  numerator_confirmed_invalid=invalid,denominator=den,uncertain_count=unknown,confirmed_invalid_rate=lo,
                  invalid_or_uncertain_rate=hi,threshold=.01,per_operation=perop)

def procurement_metric(game,trace,audit):
    seat=game['candidate_seat'];orders=[]
    for step,pair in enumerate(trace['actions']):
        for index,o in enumerate(pair[seat].get('market',[])):
            if isinstance(o,list) and o and o[0] in ('BUY_LAND','BUY_ANIMAL','BUY_SEED'):
                orders.append({'decision_step':step,'order_index':index,'op':o[0],'item':o[1] if len(o)>1 else 'land','quantity':o[2] if len(o)>2 else 1})
    diagnostics=game.get('strategy_diagnostics') or []
    own=diagnostics[seat].get(str(seat),{}) if len(diagnostics)>seat and isinstance(diagnostics[seat],dict) else {}
    return metric('PENDING','现有累计requested/confirmed及实际成交账本不能证明逐笔净目标、下一帧确认与超目标审计；不得推断缺失次数为0',
                  issued_orders=len(orders),issued_quantity=sum(z['quantity'] for z in orders),issued_order_records=orders,
                  last_decision_orders=[z for z in orders if z['decision_step']==718],
                  actual_engine_ledger=game.get('action_audit',{}).get('actual_market_ledger',[{},{}])[seat],
                  self_reported_cumulative_metrics=own.get('metrics'),self_reported_purchase_misses=own.get('purchase_misses'),
                  per_order_confirmation_coverage=None,duplicate_over_target_count=None,
                  required_evidence=['逐笔step+order_index身份','发出前真实资产/净目标缺口','真实成交量','下一可见step核对','末帧外部终态核对','未成交不减少目标缺口','重复超目标审计'])

def water_metric(game,own,events,terminal):
    seat=game['candidate_seat'];end=terminal[seat];plants=[z for z in events if z['seat']==seat and z['kind']=='plant']
    accepted=own['denominators']['plantings_all'];success=0;failed=0;unknown=[];external=[]
    for z in plants:
        water=z.get('first_water_step');day=z['planted_day'];x,y=z['position']
        if water is not None:
            if water//24==day:success+=1
            else:failed+=1
        elif z.get('planting_day_eod_observed') or end['day']>day:failed+=1
        elif end['day']==day:
            tile=end['farms'][seat]['tiles'][y][x]
            if isinstance(tile,dict) and tile.get('crop')==z['crop'] and tile.get('planted_day')==day:
                watered=bool(tile.get('watered_today'));success+=int(watered);failed+=int(not watered)
                external.append({'plant_step':z['decision_step'],'position':[x,y],'watered_today':watered,'terminal_step':end['step']})
            elif any(q['seat']==seat and q['kind']=='dig_crop' and q['position']==[x,y] and q['decision_step']>z['decision_step'] for q in events):failed+=1
            else:unknown.append({'plant_step':z['decision_step'],'position':[x,y],'reason':'末日原植物已不在终态，未找到明确首次水/销毁记录'})
        else:unknown.append({'plant_step':z['decision_step'],'reason':'终态时钟早于播种日'})
    source_count=game.get('action_audit',{}).get('unit_counts',[{},{}])[seat].get('changed_PLANT')
    if len(plants)!=accepted or source_count!=accepted:unknown.append({'reason':'实际PLANT事件、分析器分母与来源耗种成功计数不一致'})
    r=ratio(success,accepted);st='PENDING' if not accepted or unknown else 'PASS' if r>=.99 else 'FAIL'
    return metric(st,'分母为官方引擎实际接受并耗种成功的全部PLANT；未耗种的任务分派/取消不创造植物暴露',
                  actual_accepted_plantings=accepted,first_day_watered=success,first_day_not_watered=failed,unknown_count=len(unknown),unknown_events=unknown,
                  numerator=success,denominator=accepted,ratio=r,threshold=.99,external_terminal_checks=external,
                  prospective_task_assignments_or_cancellations='UNAVAILABLE_SEPARATE_DIAGNOSTIC_NOT_PLANT_DENOMINATOR')

def load_audit(directory,game,run,manifest):
    am=read(directory/'audit_manifest.json');a=read(directory/'analysis.json');v=read(directory/'validation.json')
    assert a['source_game_key']==game['key'],'AUDIT_SOURCE_GAME_MISMATCH'
    assert am['source_trace']['sha256']==game['trace']['sha256'],'AUDIT_SOURCE_TRACE_MISMATCH'
    assert am['candidate_composite_sha256']==game['candidate_composite_sha256'],'AUDIT_CANDIDATE_MISMATCH'
    assert am['engine_composite_sha256']==manifest['engine']['composite_sha256'],'AUDIT_ENGINE_MISMATCH'
    assert am['source_games']['sha256']==sha(run/'games.jsonl'),'AUDIT_SOURCE_GAMES_DRIFT'
    for name,expected in v.get('files',{}).items():
        if name in ('analysis.json','events.jsonl.gz','daily_states.json.gz','terminal_states.json'):assert sha(directory/name)==expected,('AUDIT_FILE_DRIFT',name)
    assert v.get('all_item_inventory_conservation_zero_residual') and v.get('actual_harvest_quantities_match_source') and v.get('terminal_full_snapshot_matches_source'),'AUDIT_VALIDATION_INCOMPLETE'
    events=[json.loads(z) for z in gzip.open(directory/'events.jsonl.gz','rt')]
    daily=json.load(gzip.open(directory/'daily_states.json.gz'));terminal=read(directory/'terminal_states.json')
    return a,events,daily,terminal

def game_metrics(game,manifest,run,audit_dir):
    seat=game['candidate_seat'];engine=metric('PASS','来源完整调用与异常记录满足工程观测要求',
        environment_calls=game.get('calls'),agent_calls=[z.get('calls') for z in game.get('agents',[])],errors=game.get('errors'),
        candidate_latency_ms=game.get('agents',[{},{}])[seat].get('latency_ms'),parity_pass=game.get('parity_pass'))
    known_bad=game.get('status')!='DONE' or game.get('calls')!=719 or game.get('errors') or len(game.get('agents',[]))!=2 or any(z.get('calls')!=719 for z in game.get('agents',[]))
    latency=engine['candidate_latency_ms'] or {};slow=latency.get('max')
    if known_bad or (slow is not None and slow>1000):engine['status']='FAIL';engine['reason']='已观察到调用、异常或单步时间不满足要求'
    elif slow is None:engine['status']='PENDING';engine['reason']='缺少代理单步延迟证据'
    if audit_dir is None:return {'engineering':engine,'mechanism_evidence':metric('PENDING','没有匹配且可核对的冻结机制账本')}
    trace_path=Path(game['trace']['path']);assert sha(trace_path)==game['trace']['sha256'],'TRACE_SHA_MISMATCH';trace=json.load(gzip.open(trace_path))
    a,events,daily,terminal=load_audit(audit_dir,game,run,manifest);own=a['seats'][seat];n=own['denominators']
    water=water_metric(game,own,events,terminal)
    deaths=n['plant_eod_drought_deaths'];plant_day=n['plant_eod_exposures'];plants=n['plantings_all'];escapes=n['animal_eod_escapes'];animal_day=n['animal_eod_exposures'];placed=n['animal_placed']
    pr=[ratio(deaths,plant_day),ratio(deaths,plants)];ar=[ratio(escapes,animal_day),ratio(escapes,placed)]
    loss_status='FAIL' if any(v is not None and v>.01 for v in pr+ar) else 'PENDING' if any(v is None for v in pr+ar) else 'PASS'
    losses=metric(loss_status,'两种分母都须≤1%；规则自然寿命衰败另列，未取得事前退出日志，因此所有缺水消失/逃逸均计入',
                  plant_loss=deaths,plant_eod_denominator=plant_day,planting_denominator=plants,plant_loss_per_eod=pr[0],plant_loss_per_planting=pr[1],
                  animal_loss=escapes,animal_eod_denominator=animal_day,placed_animal_denominator=placed,animal_loss_per_eod=ar[0],animal_loss_per_placed=ar[1],
                  predeclared_exit_exclusions=0,exit_evidence_status='NO_PREDECLARED_OBJECT_LOG_SUPPLIED',threshold=.01,
                  natural_standing_yield_decay=dict(own['actual_flow'].get('standing_yield_decay',{})))
    rulefiles=manifest['engine']['files'];rule_ok=any(p.endswith('/envs/kaggriculture/kaggriculture.py') and value==RULE_SHA for p,value in rulefiles.items())
    cfg=manifest['configuration'];clock_ok=cfg.get('turnsPerDay')==24 and cfg.get('episodeSteps')==720
    closing=closing_measurement(game,a,events,daily,terminal) if rule_ok and clock_ok else metric('PENDING','末日物料推导仅支持已核实1.32.7规则及720/24时钟')
    return {'engineering':engine,'action_validity':actions_metric(game,trace),'planting_first_day_water':water,'care_losses':losses,
            'procurement_confirmation_and_targets':procurement_metric(game,trace,a),'terminal_liquidation':closing}

def seat_summary(rows):
    metrics={};names=set(k for row in rows for k in row['metrics'])
    for name in sorted(names):
        zs=[r['metrics'][name] for r in rows if name in r['metrics']]
        metrics[name]={'status':status([z['status'] for z in zs]+(['PENDING'] if len(zs)!=len(rows) else [])),
                       'games_with_metric':len(zs),'pass_fail_pending':dict(collections.Counter(z['status'] for z in zs))}
    losses=[r['metrics']['care_losses'] for r in rows if 'care_losses' in r['metrics']]
    if losses:
        total={k:sum(z[k] for z in losses) for k in ['plant_loss','plant_eod_denominator','planting_denominator','animal_loss','animal_eod_denominator','placed_animal_denominator']}
        total.update(plant_loss_per_eod=ratio(total['plant_loss'],total['plant_eod_denominator']),plant_loss_per_planting=ratio(total['plant_loss'],total['planting_denominator']),
                     animal_loss_per_eod=ratio(total['animal_loss'],total['animal_eod_denominator']),animal_loss_per_placed=ratio(total['animal_loss'],total['placed_animal_denominator']))
        metrics['care_losses']['pooled_integer_numerators_denominators']=total
        rates=[total[k] for k in ['plant_loss_per_eod','plant_loss_per_planting','animal_loss_per_eod','animal_loss_per_placed']]
        metrics['care_losses']['status']='PENDING' if len(losses)!=len(rows) or any(r is None for r in rates) else 'PASS' if all(r<=.01 for r in rates) else 'FAIL'
        metrics['care_losses']['worst_individual_game_rates']={k:max((z[k] for z in losses if z[k] is not None),default=None) for k in ['plant_loss_per_eod','plant_loss_per_planting','animal_loss_per_eod','animal_loss_per_placed']}
    actions=[r['metrics']['action_validity'] for r in rows if 'action_validity' in r['metrics']]
    if actions:
        total={k:sum(z[k] for z in actions) for k in ['numerator_confirmed_invalid','denominator','uncertain_count']}
        total['confirmed_invalid_rate']=ratio(total['numerator_confirmed_invalid'],total['denominator']);total['invalid_or_uncertain_rate']=ratio(total['numerator_confirmed_invalid']+total['uncertain_count'],total['denominator'])
        metrics['action_validity']['pooled_counts']=total
        metrics['action_validity']['status']='PENDING' if len(actions)!=len(rows) or not total['denominator'] or total['uncertain_count'] else 'PASS' if total['confirmed_invalid_rate']<=.01 else 'FAIL'
        if total['denominator'] and total['confirmed_invalid_rate']>.01:metrics['action_validity']['status']='FAIL'
        metrics['action_validity']['worst_individual_confirmed_rate']=max((z['confirmed_invalid_rate'] for z in actions if z['confirmed_invalid_rate'] is not None),default=None)
    water=[r['metrics']['planting_first_day_water'] for r in rows if 'planting_first_day_water' in r['metrics']]
    if water:
        total={k:sum(z[k] for z in water) for k in ['numerator','denominator','unknown_count']};total['ratio']=ratio(total['numerator'],total['denominator'])
        metrics['planting_first_day_water']['pooled_counts']=total
        metrics['planting_first_day_water']['status']='PENDING' if len(water)!=len(rows) or not total['denominator'] or total['unknown_count'] else 'PASS' if total['ratio']>=.99 else 'FAIL'
        metrics['planting_first_day_water']['worst_individual_ratio']=min((z['ratio'] for z in water if z['ratio'] is not None),default=None)
    close=[r['metrics']['terminal_liquidation'] for r in rows if 'terminal_liquidation' in r['metrics']]
    if close:
        vals=[z['ratio'] for z in close if z.get('ratio') is not None]
        metrics['terminal_liquidation']['individual_game_ratios']=vals;metrics['terminal_liquidation']['minimum_game_ratio']=min(vals) if vals else None
        numerator=sum(z.get('numerator',0) for z in close);denominator=sum(z.get('denominator',0) for z in close);r=ratio(numerator,denominator)
        metrics['terminal_liquidation']['pooled_values']={'numerator':numerator,'denominator':denominator,'ratio':r}
        blocked=len(close)!=len(rows) or any(z['status']=='PENDING' for z in close)
        metrics['terminal_liquidation']['status']='PENDING' if blocked or not denominator else 'PASS' if r>=.95 else 'FAIL'
    return {'games':len(rows),'seeds':[r['seed'] for r in rows],'metrics':metrics,'observed_requirement_status':status([z['status'] for z in metrics.values()])}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--audit-dirs',nargs='+',type=Path,default=[])
    p.add_argument('--protocol',type=Path,default=HERE.parent/'GATE_PROTOCOL.md');p.add_argument('--aggregation-policy',type=Path,default=HERE.parent/'research/g1_aggregation_policy.json')
    p.add_argument('--registration',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    run=args.run_dir.resolve();out=args.output.resolve();out.parent.mkdir(parents=True,exist_ok=True)
    if out.with_suffix('.json').exists():raise RuntimeError('输出已存在，拒绝覆盖证据')
    m=read(run/'run_manifest.json');s=read(run/'summary.json');games=[json.loads(z) for z in (run/'games.jsonl').read_text().splitlines() if z.strip()]
    assert m['schema'] in ('v125-natural-rng-match-v1','v125-natural-rng-match-v2'),'UNSUPPORTED_RUNNER_SCHEMA'
    assert s['manifest_sha256']==digest(m),'SUMMARY_MANIFEST_MISMATCH'
    assert all(g['manifest_sha256']==digest(m) for g in games),'GAME_MANIFEST_MISMATCH'
    assert len({g['key'] for g in games})==len(games),'DUPLICATE_GAMES'
    assert s['recorded_games']==len(games) and s['done_games']==sum(g['status']=='DONE' for g in games),'SUMMARY_GAMES_NOT_FROZEN_TOGETHER'
    audits={}
    for d in args.audit_dirs:
        d=d.resolve();a=read(d/'analysis.json');key=a['source_game_key']
        assert key not in audits,'DUPLICATE_AUDIT_KEY';audits[key]=d
    selected={g['key'] for g in games};assert set(audits)<=selected,'AUDIT_OUTSIDE_SELECTED_RUN'
    protocol_sha=sha(args.protocol);policy=read(args.aggregation_policy);assert policy['protocol_sha256']==protocol_sha,'AGGREGATION_POLICY_PROTOCOL_MISMATCH';rows=[]
    for g in games:
        try:metrics=game_metrics(g,m,run,audits.get(g['key']))
        except Exception as error:metrics={'source_evidence':metric('PENDING','证据链或口径校验未通过',error=f'{type(error).__name__}: {error}')}
        if g.get('status')!='DONE' or g.get('calls')!=719 or g.get('errors'):metrics['engineering']=metric('FAIL','来源明确记录不完整调用或异常，其他证据缺失不能掩盖它',environment_calls=g.get('calls'),errors=g.get('errors'))
        for z in metrics.values():z['diagnostic_verdict']='DIAGNOSTIC_'+z['status']
        rows.append({'key':g['key'],'seed':g['seed'],'seat':g['candidate_seat'],'candidate_cash':g.get('candidate_reward'),
                     'source_game_status':g['status'],'audit_dir':str(audits[g['key']]) if g['key'] in audits else None,'metrics':metrics})
    seeds=sorted({z['seed'] for z in rows});pairs={(z['seed'],z['seat']) for z in rows};complete_pairs=len(seeds)==8 and pairs=={(seed,seat) for seed in seeds for seat in (0,1)} and len(rows)==16
    eligibility=metric('PENDING','完整G1必须事前冻结的新8seed×双席位，且微场景、全量实际PLANT/采购证据齐全；旧诊断不追认为资格通过',
                       required_seed_count=8,required_games=16,observed_seed_count=len(seeds),observed_games=len(rows),complete_8x2_shape=complete_pairs,
                       source_protocol_sha256=(m.get('protocol') or {}).get('sha256'),measuring_protocol_sha256=protocol_sha,
                       source_protocol_matches_current=(m.get('protocol') or {}).get('sha256')==protocol_sha,registration=None)
    if args.registration:
        reg=read(args.registration);eligibility['registration']={'path':str(args.registration.resolve()),'sha256':sha(args.registration),'content':reg}
        eligibility['reason']+='；登记文件仅展示，不以自报fresh或通过布尔值替代独立未使用种子与微场景审核'
    seats={str(seat):seat_summary([z for z in rows if z['seat']==seat]) if any(z['seat']==seat for z in rows) else {'games':0,'observed_requirement_status':'PENDING','reason':'缺少该候选席位数据'} for seat in (0,1)}
    observed=status([z['observed_requirement_status'] for z in seats.values()]);gate='FAIL' if observed=='FAIL' else 'PENDING'
    report={'schema':SCHEMA,'generated_at_utc':datetime.now(timezone.utc).isoformat(),'candidate_composite_sha256':m['candidate']['composite_sha256'],
            'source_run_dir':str(run),'evidence_role':'READ_ONLY_G1_MECHANISM_SUMMARY_NOT_GOLD_EVIDENCE','g1_status':gate,
            'observed_requirement_status':observed,'eligibility':eligibility,'by_seat':seats,'games':rows,'engine_runs':0,'agent_calls':0,
            'missing_evidence_policy':'没有分母、下一帧确认链、目标日志、可明确窗口或物料闭合时PENDING；发现明确超阈值时保留FAIL。',
            'aggregation_policy':{'path':str(args.aggregation_policy.resolve()),'sha256':sha(args.aggregation_policy),'content':policy},
            'aggregation_summary':'各seat分别合计分子/分母判比例，保留逐局、最差与单局失败数。异常、缺失、非闭合与采购链未核验逐局阻断，不由合计抹掉。'}
    dump(out.with_suffix('.json'),report)
    lines=['# G1只读证据汇总','',f'候选 `{m["candidate"]["composite_sha256"]}`；来源 `{run.name}`。G1状态 **{gate}**。新增引擎运行0、代理调用0。',
           '',f'完整门要求新8seed×双席位；当前{len(seeds)}seed、{len(rows)}局。实际耗种成功PLANT为首水分母；缺少的采购链和资格证据不会被默认为通过。','',
           '| seed | seat | 工程 | 动作 | 实际首日水 | 照护损失 | 采购链 | 末日兑现 | 兑现率 |','|---:|---:|---|---|---|---|---|---|---:|']
    names=['engineering','action_validity','planting_first_day_water','care_losses','procurement_confirmation_and_targets','terminal_liquidation']
    for z in rows:
        states=[z['metrics'].get(name,{}).get('diagnostic_verdict','DIAGNOSTIC_PENDING') for name in names];r=z['metrics'].get('terminal_liquidation',{}).get('ratio')
        lines.append('| '+ ' | '.join([str(z['seed']),str(z['seat']),*states,f'{r:.4%}' if r is not None else '缺失'])+' |')
    lines+=['','末日兑现以末日真实SELL量、终局剩余和末日已可售却销毁量统一按终局报价加权，包括仓内、随身、成熟田间与可收肥，排除动物、种子、未成熟产量；分母不含全季销售。末日BUY_PRODUCT、物料不闭合或零分母时PENDING。',
            '', '逐seat分别合计分子/分母判定比例，并保留逐局结果、最差值与单局失败数；异常、缺失、非闭合与采购链未核验不能被合计覆盖。首水覆盖所有官方耗种成功PLANT，缺最后观测时须外部终态补核。采购只有累计requested/confirmed仍PENDING。旧协议指纹保留，旧诊断数值过线只是DIAGNOSTIC_PASS，不追认为资格通过。']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    sources={str(p):sha(p) for p in [run/'run_manifest.json',run/'summary.json',run/'games.jsonl',args.protocol.resolve(),args.aggregation_policy.resolve()]}
    for d in audits.values():
        for name in ('audit_manifest.json','analysis.json','validation.json','events.jsonl.gz','daily_states.json.gz','terminal_states.json'):sources[str(d/name)]=sha(d/name)
    dump(out.with_suffix('.manifest.json'),{'schema':SCHEMA,'script_path':str(Path(__file__).resolve()),'script_sha256':sha(__file__),'sources':sources,
                                          'output_json_sha256':sha(out.with_suffix('.json')),'new_engine_runs':0,'new_agent_calls':0})
    print(json.dumps({'status':gate,'output':str(out.with_suffix('.json')),'games':len(rows),'seeds':len(seeds)},ensure_ascii=False))

if __name__=='__main__':main()
