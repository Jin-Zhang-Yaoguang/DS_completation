#!/usr/bin/env python3
"""按冻结R8协议只读汇总首卖时钟与伴随指标；不调用候选或引擎。"""
import argparse,collections,hashlib,importlib.util,json,statistics,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
SEEDS={1950905801,1950905802,1950905803};VERSIONS=('R7','R8');OPPONENTS=('PASS','V120')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def measure(rows):
    issues=[]
    if len(rows)!=6:issues.append('NOT_SIX_GAMES')
    values=[]
    for r in rows:
        f=r['first_sale'];t=f['restricted_elapsed_decisions']
        if f['status']!='NUMERIC_COMPLETE' or type(t) is not int or not 1<=t<=719:issues.append('PENDING_OR_INVALID_PROVENANCE:'+r['source_key']);continue
        if f['no_qualifying_sale']:
            if t!=719 or f['first_sale_step'] is not None:issues.append('NO_EVENT_CLOCK_MISMATCH')
        elif type(f['first_sale_step']) is not int or t!=f['first_sale_step']+1:issues.append('EVENT_CLOCK_MISMATCH')
        values.append(t)
    return {'status':'PENDING' if issues else 'NUMERIC_COMPLETE','issues':issues,'games':len(rows),'elapsed_sum':sum(values) if not issues else None,'T':sum(values)/6 if not issues else None,
            'no_event_count':sum(r['first_sale']['no_qualifying_sale'] is True for r in rows),'no_event_keys':[r['source_key'] for r in rows if r['first_sale']['no_qualifying_sale'] is True]}

def numeric_decision(parent,candidate):
    # 相同六局固定分母；5*候选总时间<=4*父总时间精确表达20%，避免浮点边界假失败。
    if parent['status']!='NUMERIC_COMPLETE' or candidate['status']!='NUMERIC_COMPLETE' or not parent['elapsed_sum']:return None
    return 5*candidate['elapsed_sum']<=4*parent['elapsed_sum']

def companions(rows):
    counts=collections.Counter();species=collections.Counter();products={};invalid=collections.Counter();terminal=collections.Counter()
    for r in rows:
        counts.update({k:v for k,v in r['denominators'].items() if type(v) is int})
        for k in ['purchased','placed','purchase_cash','still_in_transit','lost_before_place','placed_objects_with_actual_product_harvest']:counts['latency_'+k]+=r['latency']['total'][k]
        counts['animal_wait_sum']+=r['latency']['total']['truncated_wait']['sum'];counts['animal_live_integral']+=r['latency']['total']['actual_live_wait']['sum']
        counts['overflow_quote_value']+=r['overflow']['eod_quote_value'];species.update(r['actual_flow'].get('buy_animal',{}))
        for item in set(r['actual_flow'].get('harvested',{}))|set(r['actual_flow'].get('sell',{})):
            v=products.setdefault(item,collections.Counter());v.update({k:r['actual_flow'].get(k,{}).get(item,0) for k in ['harvested','sell','sell_cash']})
        m=r['G1_numeric_companions']['action_validity'];invalid.update({k:m[k] for k in ['numerator_confirmed_invalid','denominator','uncertain_count']})
        terminal[r['G1_numeric_companions']['terminal_liquidation']['status']]+=1
    valid=all(r['first_sale']['status']=='NUMERIC_COMPLETE' for r in rows)
    return {'raw_counts':dict(counts),'purchased_species':dict(species),'products':{k:{**v,'realized_mean_sale_price':v['sell_cash']/v['sell'] if v['sell'] else None} for k,v in products.items()},
            'early_days_0_9_cash_sum':sum(r['first_sale']['early_days_0_9_cash'] for r in rows) if valid else None,
            'early_days_0_9_units_sum':sum(r['first_sale']['early_days_0_9_units'] for r in rows) if valid else None,
            'mean_own_cash':statistics.mean(r['own_cash'] for r in rows),'mean_opponent_cash':statistics.mean(r['opponent_cash'] for r in rows),'mean_margin':statistics.mean(r['margin'] for r in rows),
            'action_validity_counts':dict(invalid),'terminal_liquidation_individual_status_counts':dict(terminal)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--batch-dir',type=Path,required=True);p.add_argument('--first-sale-dir',type=Path,required=True);p.add_argument('--latency-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True);assert not (out/'manifest.json').exists();inputs={}
    def raw(path):
        path=Path(path).resolve();data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
        if str(path) in inputs:assert inputs[str(path)]==digest
        inputs[str(path)]=digest;return data
    def read(path):return json.loads(raw(path))
    contract=read(HERE/'aggregation_v2_fix_freeze.json');assert sha(__file__)==contract['aggregator_sha256'];assert sha(HERE.parent/'development_protocol.json')==contract['protocol_sha256']
    batch=read(args.batch_dir/'manifest.json');bv=read(args.batch_dir/'validation.json');assert bv['verified_games']==24 and bv['saved_actions_replayed']==17256
    first=read(args.first_sale_dir/'first_sale.json');fm=read(args.first_sale_dir/'manifest.json');assert sha(args.first_sale_dir/'first_sale.json')==fm['output_sha256'];assert fm['script_sha256']=='d353bd04bb4f86f492295a6d197389227934db87ff98414302538a04131a9c67'
    latency=read(args.latency_dir/'results.json');lv=read(args.latency_dir/'validation.json');lm=read(args.latency_dir/'manifest.json');assert lv['input_files_unchanged'] is True
    assert lm['script']['sha256']=='d67e06b4995a946f05e2baff0d73470a176fca8a696d6ac5b8b9aaad2736cf55'
    assert sha(lm['script']['path'])==lm['script']['sha256'];inputs[lm['script']['path']]=lm['script']['sha256']
    for name,s in lv['files'].items():assert sha(args.latency_dir/name)==s;inputs[str((args.latency_dir/name).resolve())]=s
    helper=ROOT/'evaluation/summarize_g1.py';assert sha(helper)==contract['G1_helper_sha256'];inputs[str(helper)]=sha(helper);spec=importlib.util.spec_from_file_location('frozen_g1_r8_primary_companions',helper);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    rows=[];seen=set();engines=set()
    for job in batch['jobs']:
        run=Path(job['run_dir']);version='R8' if run.name.startswith('v125-r8_') else 'R7';opp='V120' if '_v120_' in run.name else 'PASS';cell=(version,opp,job['seed'],job['seat']);assert cell not in seen;seen.add(cell)
        path=run/'games.jsonl';game=json.loads(raw(path).splitlines()[job['game_index']]);rm=read(run/'run_manifest.json');audit=Path(job['output']);a=read(audit/'analysis.json');seat=game['candidate_seat'];own=a['seats'][seat]
        assert (game['seed'],seat)==(job['seed'],job['seat']);assert game['key']==job['source_key']==a['source_game_key'];assert game['calls']==719 and game['status']=='DONE' and game['errors']==[] and game['parity_pass'] is True
        assert rm['candidate']['entry_sha256']==contract['candidate_entry_sha256'][version];engines.add(game['engine_composite_sha256'])
        f=next(x for x in first['games'] if x['game_key']==game['key']);l=next(x for x in latency if x['source_game_key']==game['key'])['seats'][seat]
        assert (f['seed'],f['seat'],f['source_sha256'])==(game['seed'],seat,rm['candidate']['entry_sha256'])
        rows.append({'version':version,'opponent':opp,'seed':game['seed'],'seat':seat,'source_key':game['key'],'audit_directory':str(audit),'first_sale':f,
                     'latency':{'total':l['total'],'by_animal':l['by_animal'],'issues':l['issues']},'denominators':own['denominators'],'actual_flow':own['actual_flow'],
                     'overflow':{k:v for k,v in own['overflow'].items() if k!='first_eod_losses'},'terminal_assets':own['terminal_assets'],
                     'G1_numeric_companions':h.game_metrics(game,rm,run,audit),'own_cash':game['candidate_reward'],'opponent_cash':game['opponent_reward'],'margin':game['margin']})
    assert seen=={(v,o,s,t) for v in VERSIONS for o in OPPONENTS for s in SEEDS for t in (0,1)};assert len(engines)==1
    assert len(first['games'])==24 and len({f['game_key'] for f in first['games']})==24
    assert len(latency)==24 and len({f['source_game_key'] for f in latency})==24
    groups=[]
    for opp in OPPONENTS:
        vr={v:[r for r in rows if r['version']==v and r['opponent']==opp] for v in VERSIONS};stats={v:measure(vr[v]) for v in VERSIONS};seat_rows={};seat_ok=[]
        for seat in (0,1):
            z={};valid=True
            for v in VERSIONS:
                sr=[r for r in vr[v] if r['seat']==seat];values=[r['first_sale']['restricted_elapsed_decisions'] for r in sr]
                ok=len(sr)==3 and all(r['first_sale']['status']=='NUMERIC_COMPLETE' and type(r['first_sale']['restricted_elapsed_decisions']) is int for r in sr)
                z[v]={'n':len(sr),'elapsed_sum':sum(values) if ok else None,'mean':sum(values)/3 if ok else None};valid=valid and ok
            z['non_later']=z['R8']['elapsed_sum']<=z['R7']['elapsed_sum'] if valid else None;seat_ok.append(z['non_later']);seat_rows[str(seat)]=z
        test=numeric_decision(stats['R7'],stats['R8']);decision=None if test is None or any(s is None for s in seat_ok) else test and all(seat_ok)
        reduction=1-stats['R8']['T']/stats['R7']['T'] if test is not None else None
        groups.append({'opponent':opp,'timing':stats,'per_seat':seat_rows,'relative_T_reduction':reduction,'threshold_at_least_20_percent':test,'primary_numeric_threshold_pass':decision,'companions':{v:companions(vr[v]) for v in VERSIONS}})
    for collection in [batch['sources'],fm['input_files']]+[s['files'] for s in lm['sources']]:
        for path,s in collection.items():
            if path in inputs:assert inputs[path]==s
            assert sha(path)==s;inputs[path]=s
    assert all(sha(path)==s for path,s in inputs.items());assert sha(__file__)==contract['aggregator_sha256']
    report={'schema':'r8-first-produced-sale-development-primary-v2','role':'PREDECLARED_DEVELOPMENT_MECHANISM_NOT_G1_G2_GOLD','groups':groups,'per_game':rows,
            'data_integrity_pass':True,'all_provenance_numeric_complete':all(r['first_sale']['status']=='NUMERIC_COMPLETE' for r in rows),
            'primary_mechanism_numeric_threshold_pass':all(g['primary_numeric_threshold_pass'] is True for g in groups),'candidate_calls':0,'engine_steps':0,'new_independent_matches':0,
            'upstream_saved_actions_replayed':17256,'formal_G1_G2_Gold_decision':'NOT_ASSESSED','strength':'由根独立冻结强度校验器裁决，主机制不能覆盖强度失败。'}
    dump(out/'manifest.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(__file__),'sources':inputs,'aggregation_contract_sha256':sha(HERE/'aggregation_v2_fix_freeze.json')});dump(out/'assessment.json',report)
    dump(out/'validation.json',{'source_files_unchanged':True,'all_24_keys_complete_unique':True,'no_pending_as_zero':True,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0})
    print(json.dumps({'primary_mechanism_numeric_threshold_pass':report['primary_mechanism_numeric_threshold_pass'],'groups':[{'opponent':g['opponent'],'timing':g['timing'],'relative_T_reduction':g['relative_T_reduction'],'per_seat':g['per_seat']} for g in groups]},ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except BaseException:
        if '--output' in sys.argv:
            target=Path(sys.argv[sys.argv.index('--output')+1]);target.mkdir(parents=True,exist_ok=True);(target/'failure.txt').write_text(traceback.format_exc())
        raise
