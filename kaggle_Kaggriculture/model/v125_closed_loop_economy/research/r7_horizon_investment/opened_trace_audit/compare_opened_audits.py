#!/usr/bin/env python3
"""只读已验证的三个开放机制审计；不导入或调用候选、引擎。"""
import collections,csv,gzip,hashlib,json
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'comparison'
ANIMALS={'COW','SHEEP','GOOSE'}
PRODUCTS=['WHEAT','CARROT','TOMATO','STRAWBERRY','MELON','MILK','WOOL','EGG','FERTILIZER']
EXPERT={'WHEAT':'balanced','CARROT':'balanced','TOMATO':'horticulture','STRAWBERRY':'horticulture','MELON':'horticulture','COW':'dairy','SHEEP':'fiber','GOOSE':'other'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')

def main():
    OUT.mkdir(exist_ok=True);assert not (OUT/'manifest.json').exists()
    inputs={};rows=[];daily=[];r7_plans=[]
    def load(p):
        inputs[str(p.resolve())]=sha(p)
        return json.load(gzip.open(p)) if p.suffix=='.gz' else json.loads(p.read_text())
    latency=load(HERE/'r0_r6_r7_latency_comparison/results.json')
    audits=[('R0',ROOT/'research/mechanism_analysis/r0_pass_s0'),('R6',ROOT/'research/mechanism_analysis/r6_pass_s0'),('R7',HERE/'r7_pass_s0_mechanism')]
    for version,path in audits:
        a=load(path/'analysis.json');m=load(path/'audit_manifest.json');v=load(path/'validation.json');states=load(path/'daily_states.json.gz')
        events_path=path/'events.jsonl.gz';inputs[str(events_path.resolve())]=sha(events_path)
        with gzip.open(events_path,'rt') as f:events=[json.loads(z) for z in f]
        for name in ('analysis.json','daily_states.json.gz','events.jsonl.gz'):assert sha(path/name)==v['files'][name]
        for name in ('source_games','source_trace','source_run_manifest'):assert sha(m[name]['path'])==m[name]['sha256']
        gamepath=Path(m['source_games']['path']);inputs[str(gamepath)]=sha(gamepath);game=json.loads(gamepath.read_text().splitlines()[m['source_games']['game_index']])
        trace=load(Path(m['source_trace']['path']));s=m['candidate_seat'];own=a['seats'][s];flow=own['actual_flow'];ledger=game['action_audit']['actual_market_ledger'][s]
        assert m['seed']==1950905001 and s==0 and game['calls']==719
        own_events=[e for e in events if e['seat']==s]
        actual_plant=collections.Counter(e['crop'] for e in own_events if e['kind']=='plant')
        plant_experts=collections.Counter()
        for crop,n in actual_plant.items():plant_experts[EXPERT[crop]]+=n
        terminal_cash=game['rewards'][s]
        income=sum(ledger.get('SELL_cash',{}).values())
        cost={op:sum(ledger.get(op+'_cash',{}).values()) for op in ['BUY_ANIMAL','BUY_SEED','BUY_PRODUCT','BUY_LAND','HIRE']}
        cash_residual=3000+income-sum(cost.values())-terminal_cash
        assert cash_residual==0
        lt=next(x for x in latency if x['source_game_key']==a['source_game_key'])['seats'][s]
        products=[]
        for item in PRODUCTS:
            sold=flow.get('sell',{}).get(item,0);cash=flow.get('sell_cash',{}).get(item,0)
            products.append({'item':item,'harvested':flow.get('harvested',{}).get(item,0),'sold':sold,'sale_cash':cash,'realized_mean_sale_price':cash/sold if sold else None,
                             'bought_product':flow.get('buy_product',{}).get(item,0),'purchase_cash':flow.get('buy_product_cash',{}).get(item,0),
                             'overflow_qty':flow.get('eod_overflow',{}).get(item,0),'feed_qty':flow.get('feed',{}).get(item,0),'fertilize_qty':flow.get('fertilize',{}).get(item,0)})
        diag=game['strategy_diagnostics'][s].get(str(s),{}) if game.get('strategy_diagnostics') and isinstance(game['strategy_diagnostics'][s],dict) else {}
        receipts=diag.get('investment_receipts',[])
        first=lambda kind:next((e['decision_step'] for e in own_events if e['kind']==kind),None)
        version_row={'version':version,'source_game_key':a['source_game_key'],'candidate_entry_sha256':m['candidate_entry_sha256'],'engine_composite_sha256':m['engine_composite_sha256'],
                     'terminal_cash':terminal_cash,'opponent_cash':game['rewards'][1-s],'margin':game['margin'],'cash_income':income,'cash_costs':cost,'cash_identity_residual':cash_residual,
                     'denominators':own['denominators'],'overflow_qty':own['overflow']['eod_qty'],'overflow_quote_value':own['overflow']['eod_quote_value'],
                     'terminal_assets':own['terminal_assets'],'animal_latency':lt['total'],'by_animal':lt['by_animal'],'actual_planting_by_crop':dict(actual_plant),
                     'actual_planting_by_expert_item_family':dict(plant_experts),'products':products,'first_harvest_step':first('harvest'),'actual_hires':sum(ledger.get('HIRE_qty',{}).values())}
        rows.append(version_row)
        for d in range(30):
            de=[e for e in own_events if e['day']==d];end=next(z for z in states if (z['recorded_step']-1)//24==d)['states'][s];farm=end['farms'][s]
            planted=collections.Counter(e['crop'] for e in de if e['kind']=='plant');harvest=collections.Counter();sold=collections.Counter();revenue=collections.Counter();bought=collections.Counter()
            for e in de:
                if e['kind']=='harvest':harvest[e['item']]+=e['quantity']
                if e['kind']=='market':
                    if e['op']=='SELL':sold[e['item']]+=e['quantity'];revenue[e['item']]+=e['price']*e['quantity']
                    if e['op']=='BUY_ANIMAL':bought[e['item']]+=e['quantity']
            placed=collections.Counter(e['animal'] for e in de if e['kind']=='place_animal')
            standing=collections.Counter(t.get('animal',t.get('crop',t['kind'])) for r in farm['tiles'] for t in r if isinstance(t,dict))
            action_counts=collections.Counter();market_counts=collections.Counter()
            for pair in trace['actions'][d*24:min(719,(d+1)*24)]:
                action=pair[s]
                for cmd in [action.get('farmer',['PASS'])]+action.get('hands',[]):action_counts[cmd[0] if cmd else 'PASS']+=1
                market_counts.update(cmd[0] for cmd in action.get('market',[]) if cmd)
            daily.append({'version':version,'day':d,'last_recorded_step':end['step'],'cash_end':farm['money'],'land_end':len(farm['unlocked_quadrants']),
                          'standing_end':dict(standing),'actual_planted':dict(planted),'actual_harvest':dict(harvest),'actual_sold':dict(sold),'sale_cash':dict(revenue),
                          'animals_bought':dict(bought),'animals_placed':dict(placed),'unit_action_intents':dict(action_counts),'market_order_intents':dict(market_counts)})
            if version=='R7':
                rs=[r for r in receipts if r['step']//24==d];admitted=collections.Counter();rejects=collections.Counter();expert_frames=collections.Counter()
                for r in rs:
                    admitted.update(z['item'] for z in r['admitted']);rejects.update(r['rejected_types']);expert_frames[r['expert']]+=1
                r7_plans.append({'day':d,'expert_frames':dict(expert_frames),'admitted_quote_items_repeated_across_frames':dict(admitted),'rejected_quote_reasons_repeated_across_frames':dict(rejects),
                                 'actual_cash_min':min(r['actual_cash'] for r in rs),'actual_cash_max':max(r['actual_cash'] for r in rs),
                                 'existing_reserved_cash_max_model':max(r['existing']['reserved_cash'] for r in rs),'remaining_investment_cash_min_model':min(r['remaining_cash'] for r in rs),
                                 'first_frame':rs[0],'land_intents':[{'step':r['step'],'land_cash':r['land_cash']} for r in rs if r['land_cash']]})
        if version=='R7':
            version_row['expert_decision_frames']=dict(collections.Counter(r['expert'] for r in receipts))
            expert_permits=collections.Counter();permit_items=collections.Counter();reasons=collections.Counter()
            for r in receipts:
                expert_permits[r['expert']]+=len(r['admitted']);permit_items.update(z['item'] for z in r['admitted']);reasons.update(r['rejected_types'])
            version_row['admitted_quote_counts_by_expert_repeated']=dict(expert_permits);version_row['admitted_quote_counts_by_item_repeated']=dict(permit_items);version_row['rejected_quote_reason_counts_repeated']=dict(reasons)
            version_row['animal_place_objects']=lt['placement_objects'];version_row['animal_purchase_lots']=lt['lots']
    r6,r7=rows[1:];comparison={'r7_minus_r6_terminal_cash':r7['terminal_cash']-r6['terminal_cash'],'r7_minus_r6_margin':r7['margin']-r6['margin'],
                             'r7_minus_r6_income':r7['cash_income']-r6['cash_income'],'r7_minus_r6_costs':{k:r7['cash_costs'][k]-r6['cash_costs'][k] for k in r6['cash_costs']},
                             'truncated_wait_mean_relative_reduction':1-r7['animal_latency']['truncated_wait']['mean']/r6['animal_latency']['truncated_wait']['mean'],
                             'animal_purchase_relative_reduction':1-r7['animal_latency']['purchased']/r6['animal_latency']['purchased'],
                             'products':[{**x,'r7_minus_r6_sale_cash':x['sale_cash']-y['sale_cash']} for x,y in zip(r7['products'],r6['products'])]}
    dump(OUT/'manifest.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(__file__),'sources':inputs,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0,'evidence_role':'OPENED_SINGLE_SEED_DIAGNOSTIC_ONLY'})
    dump(OUT/'comparison.json',{'versions':rows,'r7_vs_r6':comparison});dump(OUT/'daily_economy.json',daily);dump(OUT/'r7_plan_receipts_by_day.json',r7_plans)
    with (OUT/'daily_cash.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['version','day','last_recorded_step','cash_end','land_end']);w.writeheader();w.writerows({k:r[k] for k in w.fieldnames} for r in daily)
    assert all(sha(p)==v for p,v in inputs.items())
    dump(OUT/'validation.json',{'source_sha_unchanged':True,'source_audit_fingerprints_checked':True,'cash_ledgers_closed':True,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0})
    print(json.dumps({'cash':[r['terminal_cash'] for r in rows],'R7_actual_plants':rows[2]['actual_planting_by_crop'],'R7_expert_frames':rows[2]['expert_decision_frames'],
                      'R7_permit_quotes':rows[2]['admitted_quote_counts_by_expert_repeated'],'R7_reject_quotes':rows[2]['rejected_quote_reason_counts_repeated'],'comparison':comparison},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
