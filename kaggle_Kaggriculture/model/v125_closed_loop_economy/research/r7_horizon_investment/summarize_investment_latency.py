#!/usr/bin/env python3
"""只读现有冻结机制账本，重建采购到投放的截断等待；不导入候选或引擎。"""
from __future__ import annotations
import argparse,collections,gzip,hashlib,json,statistics
from datetime import datetime,timezone
from pathlib import Path

ANALYZER_SHA='cc4d5c01a482034b55b93422e90b332e7058d6a73a096250dad39cc8eae74963'
ANIMALS=('COW','SHEEP','GOOSE')
PRODUCT={'COW':'MILK','SHEEP':'WOOL','GOOSE':'EGG'}
HORIZON=719


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def integer(value):return type(value) is int and value>=0
def describe(values):
    return {'count':len(values),'sum':sum(values),'mean':sum(values)/len(values) if values else None,
            'median':statistics.median(values) if values else None,'min':min(values) if values else None,'max':max(values) if values else None}


def summarize_seat(seat,analysis,events,terminal=None):
    """FIFO同时消费投放和库存损失；不信任旧analyzer的purchase配对。"""
    source=analysis['seats'][seat];queues={a:collections.deque() for a in ANIMALS};lots=[];placed_objects=[];active={};issues=[]
    counts=collections.defaultdict(collections.Counter);last_step=-1;unknown_objects=[]
    def issue(code,**detail):issues.append({'code':code,**detail})
    def lot(animal,step,price,index,origin='PURCHASE'):
        z={'id':f's{seat}-{animal}-{len(lots)}','animal':animal,'origin':origin,'buy_decision_step':step,'buy_event_index':index,'purchase_cash':price,
           'outcome':'IN_TRANSIT','place_decision_step':None,'loss_decision_step':None,'loss_kind':None,'placement_object_id':None}
        lots.append(z);queues[animal].append(z);return z
    for a in ANIMALS:
        initial=source.get('inventory_balance',{}).get(a,{}).get('initial',0)
        if not integer(initial):issue('INVALID_INITIAL_INVENTORY',animal=a);initial=0
        if initial:issue('INITIAL_ANIMAL_PURCHASE_TIME_UNKNOWN',animal=a,quantity=initial)
        for _ in range(initial):lot(a,None,None,None,'INITIAL_INVENTORY')
    for index,e in enumerate(events):
        if e.get('seat')!=seat:continue
        step=e.get('decision_step')
        if not integer(step) or step>=HORIZON or step<last_step or e.get('recorded_step')!=step+1:
            issue('INVALID_EVENT_CLOCK',event_index=index);continue
        last_step=step;kind=e.get('kind')
        if kind=='market' and e.get('op')=='BUY_ANIMAL':
            a=e.get('item');n=e.get('quantity')
            if a not in ANIMALS or not integer(n) or n<=0:issue('INVALID_BUY_EVENT',event_index=index);continue
            price=e.get('price')
            if type(price) not in (int,float) or price<0:issue('INVALID_BUY_PRICE',event_index=index);price=None
            for _ in range(n):lot(a,step,price,index)
            counts['buy'][a]+=n
            if e.get('total_item_after')!=len(queues[a]):issue('BUY_VISIBLE_INVENTORY_NOT_CLOSED',event_index=index,animal=a,visible=e.get('total_item_after'),queue=len(queues[a]))
        elif kind in ('manual_drop_overflow','eod_inventory_drop'):
            lost=e.get('quantity' if kind=='manual_drop_overflow' else 'discarded',{})
            for a in ANIMALS:
                n=lost.get(a,0)
                if not integer(n):issue('INVALID_LOSS_QUANTITY',event_index=index,animal=a);continue
                counts['loss'][a]+=n
                for _ in range(n):
                    if not queues[a]:issue('LOSS_WITHOUT_LIVE_LOT',event_index=index,animal=a);continue
                    z=queues[a].popleft();z.update(outcome='LOST_BEFORE_PLACE',loss_decision_step=step,loss_kind=kind,loss_event_index=index)
        elif kind=='place_animal':
            a=e.get('animal');position=e.get('position')
            if a not in ANIMALS or not isinstance(position,list) or len(position)!=2:issue('INVALID_PLACE_EVENT',event_index=index);continue
            counts['place'][a]+=1;key=tuple(position)
            z=queues[a].popleft() if queues[a] else None
            if z is None:issue('PLACE_WITHOUT_LIVE_LOT',event_index=index,animal=a)
            if key in active:issue('ACTIVE_TILE_REPLACED_WITHOUT_ESCAPE',event_index=index,prior_object_id=active[key]['id'])
            obj={'id':f's{seat}-tile-{position[0]}-{position[1]}-place-{step}-event-{index}','animal':a,'position':position,'place_decision_step':step,
                 'placed_day':step//24,'place_event_index':index,'fifo_purchase_lot_id':z['id'] if z else None,'escape_decision_step':None,
                 'first_product_harvest_step':None,'product_harvest_quantity':0,'first_fertilizer_collect_step':None,'fertilizer_collected_quantity':0,'harvest_events':[]}
            active[key]=obj;placed_objects.append(obj)
            if z is not None:
                z.update(outcome='PLACED',place_decision_step=step,placement_object_id=obj['id'])
                if z['buy_decision_step'] is not None and step<=z['buy_decision_step']:issue('PLACE_NOT_AFTER_MARKET_PURCHASE',event_index=index,lot_id=z['id'])
        elif kind in ('harvest','eod_animal_escape'):
            tile=e.get('tile_before') or {};a=tile.get('animal')
            if a is None:continue
            key=tuple(e.get('position',[]));obj=active.get(key)
            if obj is None or obj['animal']!=a or obj['placed_day']!=tile.get('placed_day'):
                issue('ANIMAL_TILE_IDENTITY_UNOBSERVED_OR_MISMATCH',event_index=index,position=list(key),animal=a)
                unknown_objects.append({'event_index':index,'kind':kind,'position':list(key),'tile_before':tile});continue
            if kind=='eod_animal_escape':
                counts['escape'][a]+=1;obj.update(escape_decision_step=step,escape_event_index=index);active.pop(key)
            else:
                n=e.get('quantity');item=e.get('item')
                if not integer(n) or n<=0:issue('INVALID_HARVEST_QUANTITY',event_index=index);continue
                if item==PRODUCT[a]:
                    if obj['first_product_harvest_step'] is None:obj['first_product_harvest_step']=step
                    obj['product_harvest_quantity']+=n;counts['product_harvest'][item]+=n
                elif item=='FERTILIZER':
                    if obj['first_fertilizer_collect_step'] is None:obj['first_fertilizer_collect_step']=step
                    obj['fertilizer_collected_quantity']+=n;counts['fertilizer_harvest'][a]+=n
                else:issue('UNEXPECTED_ANIMAL_HARVEST_PRODUCT',event_index=index,animal=a,item=item)
                obj['harvest_events'].append({'event_index':index,'decision_step':step,'item':item,'quantity':n})
    for z in lots:
        b=z['buy_decision_step']
        if b is None:
            z['truncated_wait_steps']=None;z['live_wait_steps_from_purchase']=None;continue
        endpoint=z['place_decision_step'] if z['outcome']=='PLACED' else HORIZON
        live_endpoint=z['place_decision_step'] if z['outcome']=='PLACED' else z['loss_decision_step'] if z['outcome']=='LOST_BEFORE_PLACE' else HORIZON
        z['truncated_wait_steps']=endpoint-b;z['live_wait_steps_from_purchase']=live_endpoint-b
        z['censored_at_719']=z['outcome']!='PLACED'
        if min(z['truncated_wait_steps'],z['live_wait_steps_from_purchase'])<0:issue('NEGATIVE_WAIT',lot_id=z['id'])
    purchases=[z for z in lots if z['origin']=='PURCHASE'];by_animal={}
    for a in ANIMALS:
        cohort=[z for z in purchases if z['animal']==a];placed=[z for z in cohort if z['outcome']=='PLACED'];lost=[z for z in cohort if z['outcome']=='LOST_BEFORE_PLACE'];unplaced=[z for z in cohort if z['outcome']=='IN_TRANSIT']
        actual=source.get('actual_flow',{});balance=source.get('inventory_balance',{}).get(a,{})
        checks={'event_buys_equal_official_flow':counts['buy'][a]==actual.get('buy_animal',{}).get(a,0),
                'event_places_equal_official_flow':counts['place'][a]==actual.get('placed_animal',{}).get(a,0),
                'event_losses_equal_official_flow':counts['loss'][a]==actual.get('eod_overflow',{}).get(a,0)+actual.get('manual_drop_overflow',{}).get(a,0),
                'live_queue_equal_terminal_inventory':len(queues[a])==source['terminal_assets']['inventory'].get(a,0),
                'purchased_equals_placed_live_lost':len(cohort)==len(placed)+len(lost)+len(unplaced),
                'source_inventory_residual_zero':balance.get('residual',0)==0,
                'product_harvest_equal_official_flow':counts['product_harvest'][PRODUCT[a]]==actual.get('harvested',{}).get(PRODUCT[a],0)}
        for name,ok in checks.items():
            if not ok:issue(name.upper(),animal=a)
        values=[z['truncated_wait_steps'] for z in cohort];live=[z['live_wait_steps_from_purchase'] for z in cohort]
        by_animal[a]={'purchased':len(cohort),'purchase_cash':sum(z['purchase_cash'] or 0 for z in cohort),'placed':len(placed),'still_in_transit':len(unplaced),'lost_before_place':len(lost),
                      'initial_in_transit':sum(z['origin']=='INITIAL_INVENTORY' and z['animal']==a for z in lots),
                      'truncated_wait':describe(values),'actual_live_wait':describe(live),'placed_wait':describe([z['truncated_wait_steps'] for z in placed]),
                      'censored_not_placed_count':len(lost)+len(unplaced),'terminal_inventory':source['terminal_assets']['inventory'].get(a,0),
                      'placed_objects_with_actual_product_harvest':sum(o['animal']==a and o['first_product_harvest_step'] is not None for o in placed_objects),
                      'placed_objects_without_actual_product_harvest':sum(o['animal']==a and o['first_product_harvest_step'] is None for o in placed_objects),
                      'actual_product_harvest_quantity':counts['product_harvest'][PRODUCT[a]],'fertilizer_collected_quantity':counts['fertilizer_harvest'][a],
                      'placed_escape_count':counts['escape'][a],'checks':checks,'status':'PENDING_ZERO_PURCHASE' if not cohort else 'DIAGNOSTIC_NUMERIC_COMPLETE'}
    if terminal is not None:
        board=terminal['farms'][seat]['tiles'];terminal_active={}
        for y,row in enumerate(board):
            for x,t in enumerate(row):
                if isinstance(t,dict) and t.get('animal'):terminal_active[(x,y)]=(t['animal'],t.get('placed_day'))
        if terminal_active!={k:(v['animal'],v['placed_day']) for k,v in active.items()}:issue('TERMINAL_PLACED_TILE_IDENTITIES_NOT_CLOSED')
        for a in ANIMALS:
            inv=terminal['private'];visible=inv['shed'].get(a,0)+sum(i.get(a,0) for i in inv['inventories'])
            if visible!=len(queues[a]):issue('TERMINAL_FULL_STATE_INVENTORY_NOT_CLOSED',animal=a)
            by_animal[a]['terminal_shed']=inv['shed'].get(a,0);by_animal[a]['terminal_carried']=sum(i.get(a,0) for i in inv['inventories'])
    else:issue('TERMINAL_FULL_STATE_MISSING')
    primary=describe([z['truncated_wait_steps'] for z in purchases]);physical=describe([z['live_wait_steps_from_purchase'] for z in purchases])
    total={'purchased':len(purchases),'purchase_cash':sum(z['purchase_cash'] or 0 for z in purchases),'placed':sum(z['outcome']=='PLACED' for z in purchases),
           'still_in_transit':sum(z['outcome']=='IN_TRANSIT' for z in purchases),'lost_before_place':sum(z['outcome']=='LOST_BEFORE_PLACE' for z in purchases),
           'truncated_wait':primary,'actual_live_wait':physical,'lost_penalty_extra_steps':primary['sum']-physical['sum'],
           'placed_objects_with_actual_product_harvest':sum(o['first_product_harvest_step'] is not None for o in placed_objects),
           'placed_objects_without_actual_product_harvest':sum(o['first_product_harvest_step'] is None for o in placed_objects),
           'placed_objects_with_fertilizer_only':sum(o['first_product_harvest_step'] is None and o['first_fertilizer_collect_step'] is not None for o in placed_objects)}
    if not purchases:issue('ZERO_PURCHASE_DENOMINATOR')
    return {'seat':seat,'status':'PENDING' if issues else 'DIAGNOSTIC_NUMERIC_COMPLETE','total':total,'by_animal':by_animal,
            'issues':issues,'lots':lots,'placement_objects':placed_objects,'unattributed_animal_objects':unknown_objects,
            'terminal_asset_inventory':source['terminal_assets']['inventory'],'terminal_mature_products':source['terminal_assets'].get('mature_unharvested_qty',{}),
            'attribution':'同品类FIFO会计约定；PLACE和库存损失共同消费生存队列，无物理动物ID，不追踪PICKUP携带个体。'}


def load_audit(path):
    path=path.resolve();m=json.loads((path/'audit_manifest.json').read_text());v=json.loads((path/'validation.json').read_text())
    assert m['analyzer']['sha256']==ANALYZER_SHA and sha(m['analyzer']['path'])==ANALYZER_SHA,'ANALYZER_SHA_MISMATCH'
    required=('source_trace_sha_verified','terminal_full_snapshot_matches_source','cash_rewards_match_source','actual_market_quantities_match_source','actual_harvest_quantities_match_source','all_item_inventory_conservation_zero_residual')
    assert all(v.get(k) is True for k in required) and v.get('saved_actions_replayed')==719,'SOURCE_AUDIT_NOT_VERIFIED'
    files=['analysis.json','events.jsonl.gz','terminal_states.json']
    for name in files:assert sha(path/name)==v['files'][name],('AUDIT_FILE_SHA_MISMATCH',name)
    for name in ('source_run_manifest','source_games','source_trace'):
        assert sha(m[name]['path'])==m[name]['sha256'],('SOURCE_DRIFT',name)
    a=json.loads((path/'analysis.json').read_text());terminal=json.loads((path/'terminal_states.json').read_text())
    with gzip.open(path/'events.jsonl.gz','rt') as f:events=[json.loads(x) for x in f]
    src=json.loads(Path(m['source_games']['path']).read_text().splitlines()[m['source_games']['game_index']]);assert src['key']==a['source_game_key'] and src['calls']==719 and src['status']=='DONE'
    for s in (0,1):assert a['seats'][s]['actual_flow'].get('buy_animal',{})==src['action_audit']['actual_market_ledger'][s].get('BUY_ANIMAL_qty',{})
    record={'audit_dir':str(path),'source_game_key':a['source_game_key'],'candidate_seat':m['candidate_seat'],'seed':m['seed'],'candidate_composite_sha256':m['candidate_composite_sha256'],
            'engine_composite_sha256':m['engine_composite_sha256'],'files':{str(path/n):sha(path/n) for n in files+['audit_manifest.json','validation.json']}}
    return record,a,events,terminal


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--audit-dir',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True);assert not (out/'manifest.json').exists(),'拒绝覆盖已冻结汇总'
    loaded=[load_audit(d) for d in args.audit_dir];keys=[r[0]['source_game_key'] for r in loaded];assert len(keys)==len(set(keys)),'DUPLICATE_SOURCE_GAME'
    manifest={'schema':'v125-investment-truncated-wait-v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'script':{'path':str(Path(__file__).resolve()),'sha256':sha(__file__)},
              'analyzer_sha256':ANALYZER_SHA,'horizon':HORIZON,'candidate_calls':0,'engine_steps':0,'sources':[r[0] for r in loaded],
              'definitions':{'primary':'采购到投放的截断等待（含未投放/丢失惩罚）；每笔真实采购一lot，已投放为PLACE决策步−BUY决策步，否则719−BUY决策步；均值=总等待/真实采购数。',
                             'live_integral':'同一决策步时钟的实际存活在途积分：到PLACE或DROP/EOD损失即停止，仍存活未投放到719；不将丢失后的惩罚称为物理在途。',
                             'matching':'按源events文件顺序处理，同类全局FIFO；PLACE和损失都移出队列，遗失lot永不再配给PLACE。',
                             'zero_denominator':'无采购为PENDING，不定义0均值；初始动物或缺身份链保留PENDING。',
                             'actual_product':'仅实际HARVEST得到MILK/WOOL/EGG算动物主产品已采收；FERTILIZER单列；按tile坐标、placed_day、PLACE/逃逸事件核对象，非采购个体物理归因。',
                             'qualification':'只读旧账本的数值诊断，不授予G1/G2或金牌；不合并席位阈值，不自动判断20%晋级。'}}
    dump(out/'manifest.json',manifest);games=[]
    for record,a,events,terminal in loaded:
        game={**record,'seats':[summarize_seat(s,a,events,terminal[s]) for s in (0,1)]};games.append(game)
    dump(out/'results.json',games)
    summary={'games':len(games),'candidate_calls':0,'engine_steps':0,'rows':[{'source_game_key':g['source_game_key'],'candidate_seat':g['candidate_seat'],
               'status':g['seats'][g['candidate_seat']]['status'],'total':g['seats'][g['candidate_seat']]['total']} for g in games]}
    dump(out/'summary.json',summary)
    for record,*_ in loaded:
        for f,value in record['files'].items():assert sha(f)==value,'INPUT_DRIFT'
    assert sha(__file__)==manifest['script']['sha256']
    dump(out/'validation.json',{'input_files_unchanged':True,'analyzer_unchanged':True,'candidate_calls':0,'engine_steps':0,'files':{f.name:sha(f) for f in out.iterdir() if f.is_file()}})
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
