#!/usr/bin/env python3
"""从机制账本提炼分母、首次失配、资源流与复盘表；不运行引擎或策略。"""
import argparse, collections, gzip, hashlib, json
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('audit_dir',type=Path);args=p.parse_args();d=args.audit_dir.resolve()
    audit=json.load(open(d/'audit_manifest.json'));report=json.load(open(d/'analysis.json'))
    events=[json.loads(z) for z in gzip.open(d/'events.jsonl.gz','rt')]
    source_file=Path(audit['source_games']['path']);assert sha(source_file)==audit['source_games']['sha256']
    source=json.loads(source_file.read_text().splitlines()[audit['source_games']['game_index']])
    trace=json.load(gzip.open(audit['source_trace']['path']))
    daystates=json.load(gzip.open(d/'daily_states.json.gz'))
    rs=[]
    crop_constants={'WHEAT':(2,4,0,6),'CARROT':(2,3,0,4),'TOMATO':(8,8,1,4),'STRAWBERRY':(10,10,2,4),'MELON':(10,12,0,6)}
    for seat in range(2):
        e=[z for z in events if z['seat']==seat];a=report['seats'][seat]
        crops=[]
        for z in e:
            if z['kind']!='eod_plant_death':continue
            b=z['tile_before'];first,maxday,interval,limit=crop_constants[b['crop']]
            last_production_day=b['planted_day']+first+interval*(limit-1) if interval else b['planted_day']+maxday
            exhausted=bool(interval and z['day']>=last_production_day and b['yield_units']==0)
            start=z['plant_event']['decision_step']
            history=[{'kind':v['kind'],'decision_step':v['decision_step'],'item':v.get('item'),'quantity':v.get('quantity')} for v in e
                     if v.get('position')==z['position'] and start<=v['decision_step']<=z['decision_step'] and v['kind'] in ('plant','water','harvest','fertilize')]
            crops.append({'decision_step':z['decision_step'],'day':z['day'],'position':z['position'],'crop':b['crop'],
                          'planted_day':b['planted_day'],'yield_units_at_loss':b['yield_units'],'mature_at_loss':z['mature'],
                          'past_last_production_and_zero_yield':exhausted,'last_production_day':last_production_day,
                          'classification':'产季已尽且产量为0，源码存在终止供水意图；缺少逐株事前退出日志，不能赛后豁免' if exhausted else '仍有未来生产窗口或现有产量的缺水损失',
                          'history':history})
        raw=source['action_audit']['unit_counts'][seat]
        submitted={k.removeprefix('submitted_'):v for k,v in raw.items() if k.startswith('submitted_')}
        nonmove=sum(v for k,v in submitted.items() if k not in ('PASS','NORTH','SOUTH','EAST','WEST'))
        marketsteps=[]
        for step in range(719):
            zs=[z for z in e if z['kind']=='market' and z['item']=='WHEAT' and z['decision_step']==step and z['op'] in ('BUY_PRODUCT','SELL')]
            if not zs:continue
            buy=sum(z['quantity'] for z in zs if z['op']=='BUY_PRODUCT');sell=sum(z['quantity'] for z in zs if z['op']=='SELL')
            marketsteps.append({'decision_step':step,'day':step//24,'hour':step%24,'buy_qty':buy,'sell_qty':sell,
                                'buy_cash':sum(z['price'] for z in zs if z['op']=='BUY_PRODUCT'),
                                'sell_cash':sum(z['price'] for z in zs if z['op']=='SELL'),
                                'source_orders':trace['actions'][step][seat].get('market',[]),
                                'final_wheat_total_after_market':zs[-1]['total_item_after']})
        animals=[]
        for z in a['animal_placement']['placements']:
            placed_day=z['decision_step']//24;first={'COW':8,'SHEEP':6,'GOOSE':4}[z['animal']]
            laterharvest=[v for v in e if v['kind']=='harvest' and v.get('position')==z['position'] and v['decision_step']>z['decision_step'] and v['item'] in ('MILK','WOOL','EGG')]
            animals.append({'animal':z['animal'],'purchase_step':z['purchase']['decision_step'] if z['purchase'] else None,
                            'place_step':z['decision_step'],'delay_steps_fifo':z['delay_steps'],'position':z['position'],
                            'first_product_day_by_rules':placed_day+first,'no_product_window_before_terminal':placed_day+first>29,
                            'actual_product_harvested_after_placement':sum(v['quantity'] for v in laterharvest)})
        inventory_days=[]
        for z in daystates:
            o=z['states'][seat];f=o['farms'][seat];pvt=o['private'];inv=collections.Counter(pvt['shed'])
            for q in pvt['inventories']:inv.update(q)
            board=collections.Counter(t['animal'] for row in f['tiles'] for t in row if isinstance(t,dict) and t.get('animal'))
            inventory_days.append({'recorded_step':z['recorded_step'],'day':o['day'],'hour':o['hour'],'on_board':dict(board),
                                   'unplaced':{k:inv[k] for k in ('COW','SHEEP','GOOSE') if inv[k]}})
        final_sales=collections.Counter();final_cash=collections.Counter()
        for z in e:
            if z['kind']=='market' and z['op']=='SELL' and z['day']==29:
                final_sales[z['item']]+=z['quantity'];final_cash[z['item']]+=z['price']
        rs.append({'seat':seat,'unit_action_counts':submitted,'nonpass_nonmovement_submitted':nonmove,
                   'unchanged_nonpass_count_all_ops':raw.get('unchanged_nonpass',0),
                   'plant_submitted':submitted.get('PLANT',0),'plant_successful':raw.get('changed_PLANT',0),
                   'atomic_plant_blocked_requests':raw.get('atomic_plant_blocked_requests',0),
                   'planting_contract_caveat':'这里只能核对已发出的实际PLANT动作；没有从策略恢复所有曾接受但尚未播种的任务，不能以此证明完整任务接受分母。',
                   'crop_drought_losses':crops,'drought_loss_still_productive_count':sum(not z['past_last_production_and_zero_yield'] for z in crops),
                   'drought_loss_exhausted_zero_count':sum(z['past_last_production_and_zero_yield'] for z in crops),
                   'standing_decay_events':[z for z in e if z['kind']=='standing_yield_decay'],
                   'animal_placements':animals,'animal_inventory_step_integral':sum(z['delay_steps_fifo'] for z in animals if z['delay_steps_fifo'] is not None),
                   'animal_product_window_missed_count':sum(z['no_product_window_before_terminal'] for z in animals),'animal_inventory_daily':inventory_days,
                   'wheat_trade_steps':marketsteps,'wheat_both_buy_sell_same_step_count':sum(z['buy_qty']>0 and z['sell_qty']>0 for z in marketsteps),
                   'day29_realized_sale_quantity':dict(final_sales),'day29_realized_sale_cash':dict(final_cash),
                   'day29_realized_sale_cash_total':sum(final_cash.values()),
                   'terminal_liquidation_caveat':'不使用整局累积现金作清仓分母；终局成熟未收获产物必须加入未兑现资源。此处只报真实末日销售及终局残留，不赛后新创门控比例。'})
    output={'source_audit_dir':str(d),'source_trace_sha256':audit['source_trace']['sha256'],
            'source_analyzer_sha256':audit['analyzer']['sha256'],'mechanism_gate_verdict':'NO_PROMOTION_CLAIM_FROM_SINGLE_DIAGNOSTIC',
            'intent_classification_policy':'缺水/逃逸的规则事实与是否为已计划退出分开；现有动作带没有逐株事先退出登记。',
            'seats':rs}
    dump(d/'findings.json',output)
    dump(d/'findings_manifest.json',{'script_path':str(Path(__file__).resolve()),'script_sha256':sha(__file__),
                                    'inputs':{p.name:sha(p) for p in [d/'audit_manifest.json',d/'analysis.json',d/'events.jsonl.gz',d/'daily_states.json.gz']},
                                    'output_sha256':sha(d/'findings.json'),'engine_runs':0,'candidate_calls':0})
    print(d/'findings.json')

if __name__=='__main__':main()
