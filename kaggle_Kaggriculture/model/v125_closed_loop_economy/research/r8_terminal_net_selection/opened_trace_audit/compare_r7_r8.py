#!/usr/bin/env python3
"""只读R7/R8开放同种子官方审计，保存现金桥、产出、每日轨迹与G1数值诊断。"""
import collections,gzip,hashlib,importlib.util,json,sys
from datetime import datetime,timezone
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'comparison'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def main():
    OUT.mkdir(exist_ok=True);assert not (OUT/'manifest.json').exists();sources={};rows=[];daily=[]
    def read(p):
        p=Path(p);sources[str(p.resolve())]=sha(p)
        return json.load(gzip.open(p)) if p.suffix=='.gz' else json.loads(p.read_text())
    helper=ROOT/'evaluation/summarize_g1.py';assert sha(helper)=='fe4ebdfebd652a93e0847d5330355f1280a5fcf91db4239f65bc57734dcf2399';sources[str(helper)]=sha(helper)
    spec=importlib.util.spec_from_file_location('frozen_g1_r8_diagnostic',helper);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    first=read(HERE/'r7_r8_first_sale/first_sale.json');latency=read(HERE/'r7_r8_latency/results.json')
    for name,directory in [('R7',HERE.parents[1]/'r7_horizon_investment/opened_trace_audit/r7_pass_s0_mechanism'),('R8',HERE/'r8_pass_s0_mechanism')]:
        a=read(directory/'analysis.json');am=read(directory/'audit_manifest.json');av=read(directory/'validation.json');rm=read(am['source_run_manifest']['path']);run=Path(am['source_run_manifest']['path']).parent
        for f,s in av['files'].items():assert sha(directory/f)==s;sources[str(directory/f)]=s
        for key in ['analyzer','source_run_manifest','source_games','source_trace']:assert sha(am[key]['path'])==am[key]['sha256'];sources[am[key]['path']]=am[key]['sha256']
        for k in ['candidate','opponent','engine']:
            for f,s in rm[k]['files'].items():assert sha(f)==s;sources[f]=s
        game=json.loads(Path(am['source_games']['path']).read_text().splitlines()[am['source_games']['game_index']]);seat=game['candidate_seat'];assert seat==0 and game['seed']==1950905001 and game['calls']==719 and game['errors']==[] and game['parity_pass'] is True
        own=a['seats'][seat];flow=own['actual_flow'];ledger=game['action_audit']['actual_market_ledger'][seat]
        costs={op:sum(ledger.get(op+'_cash',{}).values()) for op in ['BUY_ANIMAL','BUY_SEED','BUY_PRODUCT','BUY_LAND','HIRE']};sales=sum(ledger['SELL_cash'].values());cash=game['candidate_reward'];assert 3000+sales-sum(costs.values())==cash
        with gzip.open(directory/'events.jsonl.gz','rt') as f:events=[json.loads(z) for z in f if z.strip()]
        own_events=[e for e in events if e['seat']==seat];states=read(directory/'daily_states.json.gz');trace=read(am['source_trace']['path'])
        plantings=collections.Counter(e['crop'] for e in own_events if e['kind']=='plant');fs=next(r for r in first['games'] if r['game_key']==game['key']);lt=next(r for r in latency if r['source_game_key']==game['key'])['seats'][seat]
        companions=h.game_metrics(game,rm,run,directory);diag=game['strategy_diagnostics'][seat][str(seat)]
        products={}
        for item in sorted(set(flow.get('harvested',{}))|set(flow.get('sell',{}))):
            n=flow.get('sell',{}).get(item,0);v=flow.get('sell_cash',{}).get(item,0)
            products[item]={'harvested':flow.get('harvested',{}).get(item,0),'sold':n,'sale_cash':v,'mean_realized_sale_price':v/n if n else None}
        rows.append({'version':name,'source_key':game['key'],'source_sha256':am['candidate_entry_sha256'],'engine_sha256':game['engine_composite_sha256'],'audit_directory':str(directory),
                     'cash':cash,'opponent_cash':game['opponent_reward'],'margin':game['margin'],'sales_cash':sales,'costs':costs,'cash_bridge_residual':0,
                     'first_produced_sale':fs,'animal_latency':lt,'actual_plantings':dict(plantings),'actual_flow':flow,'products':products,'denominators':own['denominators'],
                     'overflow':own['overflow'],'terminal_assets':own['terminal_assets'],'G1_numeric_companions_not_full_gate':companions,
                     'strategy_metrics_self_reported':diag['metrics'],'actual_hires':sum(ledger['HIRE_qty'].values())})
        for d in range(30):
            own_day=[e for e in own_events if e['day']==d];end=next(z for z in states if (z['recorded_step']-1)//24==d)['states'][seat];farm=end['farms'][seat]
            counters={key:collections.Counter() for key in ['harvested','sell','sell_cash','buy_animal','plant','place_animal']}
            for e in own_day:
                k=e['kind']
                if k=='harvest':counters['harvested'][e['item']]+=e['quantity']
                if k=='plant':counters['plant'][e['crop']]+=1
                if k=='place_animal':counters['place_animal'][e['animal']]+=1
                if k=='market' and e['op']=='SELL':counters['sell'][e['item']]+=e['quantity'];counters['sell_cash'][e['item']]+=e['price']*e['quantity']
                if k=='market' and e['op']=='BUY_ANIMAL':counters['buy_animal'][e['item']]+=e['quantity']
            actions=collections.Counter()
            for pair in trace['actions'][d*24:min(719,(d+1)*24)]:
                z=pair[seat]
                for cmd in [z.get('farmer',['PASS'])]+z.get('hands',[]):actions[cmd[0] if cmd else 'PASS']+=1
            daily.append({'version':name,'day':d,'cash_end':farm['money'],'land_end':len(farm['unlocked_quadrants']),
                          'standing_end':dict(collections.Counter(t.get('animal',t.get('crop',t['kind'])) for r in farm['tiles'] for t in r if isinstance(t,dict))),
                          'actual_flow':{k:dict(v) for k,v in counters.items()},'unit_action_intents':dict(actions)})
    r7,r8=rows;assert r7['engine_sha256']==r8['engine_sha256'];bridge={'delta_cash':r8['cash']-r7['cash'],'delta_opponent_cash':r8['opponent_cash']-r7['opponent_cash'],'delta_margin':r8['margin']-r7['margin'],
                                                                  'delta_sale_cash':r8['sales_cash']-r7['sales_cash'],'delta_costs':{k:r8['costs'][k]-r7['costs'][k] for k in r7['costs']}}
    bridge['residual']=bridge['delta_cash']-bridge['delta_sale_cash']+sum(bridge['delta_costs'].values());assert bridge['residual']==0
    report={'evidence_role':'OPENED_SINGLE_SEED_DIAGNOSTIC_NOT_QUALIFICATION','versions':rows,'r8_minus_r7_cash_bridge':bridge,
            'first_sale_elapsed_relative_reduction':1-r8['first_produced_sale']['restricted_elapsed_decisions']/r7['first_produced_sale']['restricted_elapsed_decisions'],
            'candidate_calls':0,'engine_steps':0,'new_independent_matches':0,'upstream_r8_saved_actions_replayed':719,'formal_G1_G2_Gold':'NOT_ASSESSED'}
    assert all(sha(p)==s for p,s in sources.items());dump(OUT/'manifest.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(__file__),'sources':sources,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0})
    dump(OUT/'comparison.json',report);dump(OUT/'daily_economy.json',daily);dump(OUT/'validation.json',{'all_sources_unchanged':True,'same_engine':True,'cash_bridge_residual_zero':True,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0})
    print(json.dumps({'cash_bridge':bridge,'R8_G1_companion_states':{k:v.get('status') for k,v in r8['G1_numeric_companions_not_full_gate'].items()},'first_sale_elapsed_relative_reduction':report['first_sale_elapsed_relative_reduction']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
