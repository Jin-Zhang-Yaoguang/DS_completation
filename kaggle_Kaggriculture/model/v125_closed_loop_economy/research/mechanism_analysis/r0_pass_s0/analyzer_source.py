#!/usr/bin/env python3
"""只重放已存动作的 G1 机制账本；不导入、不调用候选。"""
from __future__ import annotations
import argparse, copy, gzip, hashlib, importlib.util, json, statistics
from collections import Counter, defaultdict, deque
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def plain(x): return json.loads(json.dumps(x))
def dump(p, x): p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')
def stock(p):
    z = Counter(p['shed'])
    for inv in p['inventories']: z.update(inv)
    return +z
def tiles(f, pred):
    return {(x, y): copy.deepcopy(t) for y, row in enumerate(f['tiles']) for x, t in enumerate(row) if isinstance(t, dict) and pred(t)}

class Audit:
    def __init__(self, rules, engine):
        self.r, self.e, self.orig = rules, engine, {}
        self.events, self.plants, self.plant_index, self.orders, self.daily = [], [], {}, [], []
        self.counters = [Counter(), Counter()]
        self.flow = [defaultdict(Counter), defaultdict(Counter)]
        self.animal_lots = [defaultdict(deque), defaultdict(deque)]
        self.placements = []
        self.step = 0
    def emit(self, kind, seat, **kw):
        z = {'kind': kind, 'seat': seat, 'decision_step': self.step, 'recorded_step': self.step+1,
             'day': self.step//24, 'hour': self.step%24, **kw}
        self.events.append(z)
        return z
    def bind(self, state, env, logs=None):
        self.farms = {id(f): s for s, f in enumerate(state[0].observation.farms)}
        self.privates = {id(z.observation.private): s for s, z in enumerate(state)}
        self.state = state
        self.step = state[0].observation.step
        return self.interpreter(state, env)
    def wrap(self, name, f):
        self.orig[name] = getattr(self.r, name)
        setattr(self.r, name, f)
    def prices(self): return dict(self.state[0].observation.market.prices)
    def __enter__(self):
        self.interpreter = self.e.g.interpreter
        self.e.g.interpreter = self.bind
        self.wrap('_apply_unit_action', self.unit)
        self.wrap('_commit_unit', self.commit)
        self.wrap('_daily_refresh_plants', self.eod_plants)
        self.wrap('_daily_refresh_animals', self.eod_animals)
        self.wrap('_drop_inventories_to_shed', self.eod_drop)
        self.wrap('_decay_plants', self.decay)
        return self
    def __exit__(self, *_):
        self.e.g.interpreter = self.interpreter
        for k, v in self.orig.items(): setattr(self.r, k, v)
    def unit(self, farm, private, idx, action, *args, **kw):
        s = self.farms[id(farm)]
        pos = self.r._farmer_position(farm, idx)
        if pos is None: return self.orig['_apply_unit_action'](farm, private, idx, action, *args, **kw)
        x, y = pos
        op = action[0] if action else 'MALFORMED'
        bt = copy.deepcopy(farm['tiles'][y][x])
        bi = Counter(private['inventories'][idx]); bs = Counter(private['shed']); bst = stock(private)
        rv = self.orig['_apply_unit_action'](farm, private, idx, action, *args, **kw)
        at = copy.deepcopy(farm['tiles'][y][x]); ai = Counter(private['inventories'][idx]); ast = stock(private)
        c = dict(unit=idx, position=[x, y], action=action)
        if op == 'PLANT' and bt is None and isinstance(at, dict) and at.get('crop'):
            self.counters[s]['successful_plantings'] += 1
            p = self.emit('plant', s, **c, crop=at['crop'], planted_day=at['planted_day'], first_water_step=None,
                          planting_day_eod_observed=False, watered_on_planting_day=None, terminal=False)
            self.plants.append(p); self.plant_index[(s, x, y)] = p
        if op == 'WATER' and isinstance(bt, dict) and at != bt:
            self.counters[s]['successful_water'] += 1
            p = self.plant_index.get((s, x, y))
            if p is not None and p['first_water_step'] is None: p['first_water_step'] = self.step
            self.emit('water', s, **c, crop=at['crop'], planted_day=at['planted_day'])
        if op in ('HARVEST', 'COLLECT_FERTILIZER'):
            made = ai - bi
            for item, n in made.items():
                self.flow[s]['harvested'][item] += n
                self.emit('harvest', s, **c, item=item, quantity=n, tile_before=bt)
        if op in ('FEED', 'FERTILIZE'):
            used = bi - ai
            for item, n in used.items():
                self.flow[s][op.lower()][item] += n
                self.emit(op.lower(), s, **c, item=item, quantity=n, tile_before=bt)
        if op == 'DROP':
            loss = bst - ast
            if loss:
                self.flow[s]['manual_drop_overflow'].update(loss)
                self.emit('manual_drop_overflow', s, **c, quantity=dict(loss), shed_before=dict(bs), inventory_before=dict(bi),
                          quote_prices=self.prices(), quote_value=sum(n*self.prices().get(k,0) for k,n in loss.items()))
        if op == 'PLACE' and isinstance(at, dict) and at.get('animal') and (not isinstance(bt, dict) or not bt.get('animal')):
            item = at['animal']; self.flow[s]['placed_animal'][item] += 1
            lot = self.animal_lots[s][item].popleft() if self.animal_lots[s][item] else None
            row = self.emit('place_animal', s, **c, animal=item, purchase=lot,
                            delay_steps=self.step-lot['decision_step'] if lot else None,
                            delay_days=(self.step//24)-(lot['decision_step']//24) if lot else None,
                            attribution='同类采购全局 FIFO 归因；原引擎无动物个体 ID')
            self.placements.append(row)
        if op == 'DIG' and isinstance(bt, dict) and bt.get('crop') and at is None:
            mature = self.step//24-bt['planted_day'] >= self.r.CROPS[bt['crop']]['first_yield_day']
            self.emit('dig_crop', s, **c, crop=bt['crop'], yield_units=bt.get('yield_units',0), mature=mature, tile_before=bt)
        return rv
    def commit(self, op, item, price, farm, private, market, *args, **kw):
        s = self.farms[id(farm)]
        before = private['shed'].get(item, 0)
        ok = self.orig['_commit_unit'](op, item, price, farm, private, market, *args, **kw)
        if ok:
            row = self.emit('market', s, op=op, item=item, quantity=1, price=price,
                            shed_item_before=before, shed_item_after=private['shed'].get(item,0),
                            total_item_after=stock(private).get(item,0))
            self.orders.append(row)
            self.flow[s][op.lower()][item] += 1
            self.flow[s][op.lower()+'_cash'][item] += price
            if op == 'BUY_ANIMAL': self.animal_lots[s][item].append(dict(decision_step=self.step, day=self.step//24, price=price))
        return ok
    def eod_plants(self, farm, day, *args, **kw):
        s = self.farms[id(farm)]
        before = tiles(farm, lambda t:t.get('kind')=='PLANT')
        rv = self.orig['_daily_refresh_plants'](farm, day, *args, **kw)
        for (x,y), bt in before.items():
            self.counters[s]['plant_eod_exposures'] += 1
            if not bt['watered_today']: self.counters[s]['plant_unwatered_eod_exposures'] += 1
            p = self.plant_index.get((s,x,y))
            if p is not None and bt['planted_day']==day:
                p['planting_day_eod_observed']=True; p['watered_on_planting_day']=bool(bt['watered_today'])
                self.counters[s]['planting_day_eod_exposures'] += 1
                self.counters[s]['planting_day_watered' if bt['watered_today'] else 'planting_day_not_watered'] += 1
            at = farm['tiles'][y][x]
            if not isinstance(at,dict) or at.get('kind')!='PLANT':
                self.counters[s]['plant_eod_drought_deaths'] += 1
                self.emit('eod_plant_death',s,position=[x,y],crop=bt['crop'],tile_before=bt,
                          reason='连续未浇水达到2；播种时初始计数已为1', plant_event=p,
                          unharvested_yield_units=bt.get('yield_units',0),
                          mature=day-bt['planted_day']>=self.r.CROPS[bt['crop']]['first_yield_day'])
        return rv
    def eod_animals(self, farm, day):
        s=self.farms[id(farm)];before=tiles(farm,lambda t:bool(t.get('animal')))
        rv=self.orig['_daily_refresh_animals'](farm,day)
        for (x,y),bt in before.items():
            self.counters[s]['animal_eod_exposures']+=1
            if not bt['fed_today']:self.counters[s]['animal_unfed_eod_exposures']+=1
            at=farm['tiles'][y][x]
            if not isinstance(at,dict) or not at.get('animal'):
                self.counters[s]['animal_eod_escapes']+=1
                self.emit('eod_animal_escape',s,position=[x,y],animal=bt['animal'],tile_before=bt,reason='连续未喂养达到2')
        return rv
    def eod_drop(self, private, capacity):
        s=self.privates[id(private)];before=stock(private);shed=dict(private['shed']);invs=plain(private['inventories'])
        rv=self.orig['_drop_inventories_to_shed'](private,capacity);after=stock(private);loss=before-after
        self.counters[s]['inventory_eod_events']+=1
        self.flow[s]['eod_overflow'].update(loss)
        self.emit('eod_inventory_drop',s,capacity=capacity,shed_before=shed,inventories_before=invs,shed_after=dict(private['shed']),
                  dropped_into_shed=dict(Counter(private['shed'])-Counter(shed)),discarded=dict(loss),
                  quote_prices=self.prices(),quote_value=sum(n*self.prices().get(k,0) for k,n in loss.items()))
        if loss:self.counters[s]['inventory_eod_overflow_events']+=1
        return rv
    def decay(self, farm, step):
        s=self.farms[id(farm)];before=tiles(farm,lambda t:t.get('kind')=='PLANT')
        rv=self.orig['_decay_plants'](farm,step)
        for (x,y),bt in before.items():
            at=farm['tiles'][y][x]
            newqty=at.get('yield_units',0) if isinstance(at,dict) else 0
            if newqty<bt.get('yield_units',0):
                n=bt['yield_units']-newqty;self.flow[s]['standing_yield_decay'][bt['crop']]+=n
                self.emit('standing_yield_decay',s,position=[x,y],crop=bt['crop'],quantity=n,tile_before=bt,
                          became_weed=isinstance(at,dict) and at.get('kind')=='WEED')
        return rv

def terminal_assets(o,r):
    s=o['player']; f=o['farms'][s];prices=o['market']['prices'];rows=[]
    for (x,y),t in tiles(f,lambda t:bool(t.get('crop') or t.get('animal'))).items():
        item=t.get('crop') or r.ANIMALS[t['animal']]['product']
        mature=t.get('animal') is not None or o['day']-t['planted_day']>=r.CROPS[item]['first_yield_day']
        n=t.get('yield_units',0)
        if n>0:rows.append({'position':[x,y],'item':item,'quantity':n,'mature_harvestable_by_rules':mature,
                            'terminal_quote':prices.get(item,0),'quote_value':n*prices.get(item,0),'tile':t})
    fertilizer=[{'position':[x,y],'animal':t['animal'],'quantity':1} for (x,y),t in tiles(f,lambda t:bool(t.get('animal') and t.get('fertilizer_available'))).items()]
    m=Counter();imm=Counter()
    for z in rows:(m if z['mature_harvestable_by_rules'] else imm).update({z['item']:z['quantity']})
    return {'inventory':dict(stock(o['private'])),'seeds':o['private']['seeds'],'standing_products':rows,
            'mature_unharvested_qty':dict(m),'immature_standing_qty':dict(imm),'mature_quote_value':sum(n*prices.get(k,0) for k,n in m.items()),
            'uncollected_fertilizer':fertilizer,'uncollected_fertilizer_quote_value':len(fertilizer)*prices.get('FERTILIZER',0),
            'valuation_policy':'终局报价乘数量仅为未兑现资源标价；尚需采收搬运销售，已无剩余动作，且逐单位真实成交价会变化。不是现金收益、可实现回报或利润。'}

def summarize(a, source, initial, terminal):
    seats=[]
    for s in range(2):
        f=a.flow[s];events=[z for z in a.events if z['seat']==s];c=a.counters[s]
        allitems=set(initial[s])|set(terminal[s]['inventory'])
        for k in ['harvested','buy_product','buy_animal','sell','feed','fertilize','placed_animal','eod_overflow','manual_drop_overflow']:allitems.update(f[k])
        balance={}
        for item in sorted(allitems):
            vals={k:f[k].get(item,0) for k in ['harvested','buy_product','buy_animal','sell','feed','fertilize','placed_animal','eod_overflow','manual_drop_overflow']}
            res=initial[s].get(item,0)+vals['harvested']+vals['buy_product']+vals['buy_animal']-sum(vals[k] for k in ['sell','feed','fertilize','placed_animal','eod_overflow','manual_drop_overflow'])-terminal[s]['inventory'].get(item,0)
            balance[item]={'initial':initial[s].get(item,0),**vals,'terminal_inventory':terminal[s]['inventory'].get(item,0),'residual':res}
        loop=[]
        for item in sorted(set(f['buy_product'])|set(f['sell'])):
            buy=f['buy_product'][item];sell=f['sell'][item];made=f['harvested'][item];lower=max(0,sell-made-initial[s].get(item,0))
            byday=[]
            for day in range(30):
                es=[z for z in events if z['kind']=='market' and z['item']==item and z['day']==day]
                if es:
                    d={'day':day}
                    for op in ['BUY_PRODUCT','SELL']:
                        zs=[z for z in es if z['op']==op];d[op+'_qty']=len(zs);d[op+'_cash']=sum(z['price'] for z in zs)
                    byday.append(d)
            alternations=[];last=None
            for z in [z for z in events if z['kind']=='market' and z['item']==item and z['op'] in ['BUY_PRODUCT','SELL']]:
                if last and last['op']!=z['op']:
                    alternations.append({'from_op':last['op'],'from_step':last['decision_step'],'to_op':z['op'],'to_step':z['decision_step'],
                                         'gap_steps':z['decision_step']-last['decision_step'],'from_price':last['price'],'to_price':z['price'],
                                         'shed_before_to':z['shed_item_before'],'total_item_after_to':z['total_item_after']})
                last=z
            if buy:
                loop.append({'item':item,'bought':buy,'harvested':made,'sold':sell,'buy_cash':f['buy_product_cash'][item],
                             'sell_cash':f['sell_cash'][item],'sale_minus_purchase_cash_not_profit':f['sell_cash'][item]-f['buy_product_cash'][item],
                             'purchased_units_resold_lower_bound':lower,'lower_bound_fraction_of_buys':lower/buy,
                             'lower_bound_reason':'销售量 - 初始库存 - 本局实际采收量；同类商品无个体标签，不能精确区分哪一单位被转售。',
                             'by_day':byday,'buy_sell_direction_switch_count':len(alternations),'first_switches':alternations[:30],
                             'switches_within_1_step':sum(z['gap_steps']<=1 for z in alternations)})
        placements=[z for z in a.placements if z['seat']==s];delays=[z['delay_steps'] for z in placements if z['delay_steps'] is not None]
        plantrows=[z for z in a.plants if z['seat']==s]
        denominators={'plantings_all':len(plantrows),'planting_day_eod_observed':c['planting_day_eod_exposures'],
                      'planting_day_watered':c['planting_day_watered'],'planting_day_not_watered':c['planting_day_not_watered'],
                      'planting_day_eod_not_observed':len(plantrows)-c['planting_day_eod_exposures'],
                      'plant_eod_exposures':c['plant_eod_exposures'],'plant_unwatered_eod_exposures':c['plant_unwatered_eod_exposures'],
                      'plant_eod_drought_deaths':c['plant_eod_drought_deaths'],'plant_drought_death_per_plant_eod':c['plant_eod_drought_deaths']/c['plant_eod_exposures'] if c['plant_eod_exposures'] else None,
                      'plant_drought_death_per_successful_planting':c['plant_eod_drought_deaths']/len(plantrows) if plantrows else None,
                      'animal_placed':len(placements),'animal_eod_exposures':c['animal_eod_exposures'],
                      'animal_unfed_eod_exposures':c['animal_unfed_eod_exposures'],'animal_eod_escapes':c['animal_eod_escapes'],
                      'animal_escape_per_animal_eod':c['animal_eod_escapes']/c['animal_eod_exposures'] if c['animal_eod_exposures'] else None}
        loss=[z for z in events if z['kind']=='eod_inventory_drop' and z['discarded']]
        seats.append({'seat':s,'counters':dict(c),'denominators':denominators,'inventory_balance':balance,'all_inventory_residual_zero':all(z['residual']==0 for z in balance.values()),
                      'overflow':{'eod_events':len(loss),'eod_qty':dict(f['eod_overflow']),'eod_quote_value':sum(z['quote_value'] for z in loss),
                                  'manual_drop_qty':dict(f['manual_drop_overflow']),'first_eod_losses':loss[:10]},
                      'plant_first_failures':[z for z in events if z['kind']=='eod_plant_death'][:12],
                      'animal_placement':{'count':len(placements),'delay_steps_min':min(delays) if delays else None,'delay_steps_median':statistics.median(delays) if delays else None,
                                          'delay_steps_max':max(delays) if delays else None,'unplaced_fifo_lots':{k:list(v) for k,v in a.animal_lots[s].items() if v},'placements':placements},
                      'product_cycles':loop,'terminal_assets':terminal[s],'actual_flow':{k:dict(v) for k,v in f.items()}})
    return {'source_game_key':source['key'],'evidence_role':'SAME_SAVED_ACTION_TRACE_MECHANISM_DIAGNOSTIC_NOT_NEW_MATCH_OR_GOLD_EVIDENCE',
            'cash_result':source['rewards'],'seats':seats,
            'definitions':{'decision_step':'动作读取的旧 obs.step；执行后 recorded_step=decision_step+1。719个动作是step0..718。',
                           'plant_day_eod_denominator':'成功播种后，播种当日确实经过 EOD 的种植事件；终局日没有 EOD，不以未观察当失败。',
                           'unexpected_eod_loss':'这里只把规则识别的缺水死亡/饥饿逃逸列为非预期照护损失；寿命衰败、主动挖除独列，不自动视为策略错误。',
                           'inventory_balance':'初始 + 实际采购 + 实际采收 - 实际销售 - 喂养/施肥 - 放置动物 - 仓满销毁 - 末库存；成熟未收获产物尚未入库存，单列。',
                           'animal_delay':'同类动物采购与放置按全局FIFO对应的诊断时延，无实体ID；不是可识别个体追踪。',
                           'action_effect':'状态变化不等于有经济价值；无非法动作不等于机制闭环完成。'}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--game-index',type=int,default=0);args=p.parse_args()
    run=args.run_dir.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'analysis.json').exists():raise RuntimeError('目标已存在分析结果，拒绝静默覆盖；请使用新目录')
    manifest=json.load(open(run/'run_manifest.json'));source=json.loads((run/'games.jsonl').read_text().splitlines()[args.game_index]);tracepath=Path(source['trace']['path'])
    assert source['status']=='DONE' and source['calls']==719
    assert sha(tracepath)==source['trace']['sha256']
    trace=json.load(gzip.open(tracepath));assert trace['seed']==source['seed'] and len(trace['actions'])==719
    harness=Path(manifest['harness']['path']);assert sha(harness)==manifest['harness']['sha256']
    for key in ['engine','candidate','opponent']:
        for path,h in manifest[key]['files'].items():assert sha(path)==h,('source_sha_drift',path)
    spec=importlib.util.spec_from_file_location('v125_mechanism_harness_helpers',harness);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    make,rules,fast,eng=h.import_engines();assert eng['composite_sha256']==manifest['engine']['composite_sha256']
    freeze={'schema':'v125-g1-action-replay-audit-v1','created_at':datetime.now(timezone.utc).isoformat(),
            'analyzer':{'path':str(Path(__file__).resolve()),'sha256':sha(__file__)},'source_run_manifest':{'path':str(run/'run_manifest.json'),'sha256':sha(run/'run_manifest.json')},
            'source_games':{'path':str(run/'games.jsonl'),'sha256':sha(run/'games.jsonl'),'game_index':args.game_index},
            'source_trace':{'path':str(tracepath),'sha256':sha(tracepath)},'candidate_entry_sha256':manifest['candidate']['entry_sha256'],
            'candidate_composite_sha256':source['candidate_composite_sha256'],'engine_composite_sha256':eng['composite_sha256'],
            'seed':trace['seed'],'candidate_seat':source['candidate_seat'],'candidate_imported':False,'agent_calls':0,'workers':1,
            'source_episode_reused_not_new_evaluation':True,'new_official_daily_or_blind_replays_opened':False}
    dump(out/'audit_manifest.json',freeze)
    e=h.Engine('official',trace['seed'],make,fast)
    initial=[stock(e.observe(s)['private']) for s in range(2)]
    audit=Audit(rules,e)
    with audit:
        for idx,actions in enumerate(trace['actions']):
            assert e.observe(0)['step']==idx
            e.step(copy.deepcopy(actions))
            if (idx+1)%24==0 or idx==718:
                audit.daily.append({'recorded_step':idx+1,'states':[e.observe(s) for s in range(2)]})
    terminal=[e.observe(s) for s in range(2)]
    snap=h.snapshot(terminal)
    assert snap==source['terminal'],h.first_difference(snap,source['terminal'])
    assert e.rewards()==source['rewards'] and e.done()
    assets=[terminal_assets(o,rules) for o in terminal]
    report=summarize(audit,source,initial,assets)
    for s in range(2):
        assert report['seats'][s]['all_inventory_residual_zero'],report['seats'][s]['inventory_balance']
        expected=source['action_audit']['harvest_qty'][s]
        assert dict(audit.flow[s]['harvested'])==expected,(s,dict(audit.flow[s]['harvested']),expected)
        for op in ['BUY_PRODUCT','BUY_ANIMAL','BUY_SEED','SELL']:
            expected=source['action_audit']['actual_market_ledger'][s].get(op+'_qty',{})
            assert dict(audit.flow[s][op.lower()])==expected,(op,expected,dict(audit.flow[s][op.lower()]))
    for path,hsh in manifest['engine']['files'].items():assert sha(path)==hsh
    dump(out/'analysis.json',report)
    dump(out/'plant_lifetimes.json',audit.plants)
    dump(out/'terminal_states.json',terminal)
    with gzip.open(out/'events.jsonl.gz','wt') as z:
        for event in audit.events:z.write(json.dumps(event,ensure_ascii=False)+'\n')
    with gzip.open(out/'daily_states.json.gz','wt') as z:json.dump(audit.daily,z,ensure_ascii=False)
    checks={'source_trace_sha_verified':True,'source_candidate_sha_verified_without_import':True,'source_engine_composite_sha_verified':True,
            'terminal_full_snapshot_matches_source':True,'cash_rewards_match_source':True,'actual_market_quantities_match_source':True,
            'actual_harvest_quantities_match_source':True,'all_item_inventory_conservation_zero_residual':True,'agent_calls':0,'saved_actions_replayed':len(trace['actions']),
            'files':{f.name:sha(f) for f in out.iterdir() if f.is_file()}}
    dump(out/'validation.json',checks)
    own=report['seats'][source['candidate_seat']]
    print(json.dumps({'output':str(out),'denominators':own['denominators'],'overflow':own['overflow'],'terminal_assets':own['terminal_assets'],
                      'wheat_balance':own['inventory_balance'].get('WHEAT'),'animal_delays':{k:v for k,v in own['animal_placement'].items() if k!='placements'}},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
