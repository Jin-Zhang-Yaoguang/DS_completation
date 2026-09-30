#!/usr/bin/env python3
"""只读24条冻结审计，按事前规定的原分子/原分母计算开发主机制。"""
import collections,hashlib,importlib.util,json,statistics,sys
from datetime import datetime,timezone
from pathlib import Path

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
SEEDS={1950905701,1950905702,1950905703}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def ratio(a,b):return a/b if b else None

def aggregate(rows):
    counter=collections.Counter();species={};products={};loss=collections.Counter();overflow=collections.Counter();invalid=collections.Counter();closing=collections.Counter()
    for r in rows:
        t=r['latency']['total'];counter.update({k:t[k] for k in ['purchased','purchase_cash','placed','still_in_transit','lost_before_place','placed_objects_with_actual_product_harvest','placed_objects_without_actual_product_harvest']})
        counter['truncated_wait_sum']+=t['truncated_wait']['sum'];counter['live_wait_sum']+=t['actual_live_wait']['sum']
        for animal,z in r['latency']['by_animal'].items():
            c=species.setdefault(animal,collections.Counter());c.update({k:z[k] for k in ['purchased','placed','still_in_transit','lost_before_place','actual_product_harvest_quantity','fertilizer_collected_quantity']});c['truncated_wait_sum']+=z['truncated_wait']['sum']
        for item in set().union(*(set(r['actual_flow'].get(k,{})) for k in ['harvested','sell','sell_cash'])):
            c=products.setdefault(item,collections.Counter());c.update({k:r['actual_flow'].get(k,{}).get(item,0) for k in ['harvested','sell','sell_cash']})
        loss.update(r['denominators']);overflow.update(r['overflow']['eod_qty']);counter['overflow_quote_value']+=r['overflow']['eod_quote_value']
        a=r['companions']['action_validity'];invalid.update({k:a[k] for k in ['numerator_confirmed_invalid','denominator','uncertain_count']})
        c=r['companions']['terminal_liquidation'];closing[c['status']]+=1
    raw_denominators={k:v for k,v in loss.items() if not k.startswith('plant_drought_death_per_') and not k.startswith('animal_escape_per_')}
    return {'games':len(rows),'zero_purchase_games':sum(r['latency']['total']['purchased']==0 for r in rows),'totals':dict(counter),
            'D':ratio(counter['truncated_wait_sum'],counter['purchased']),'actual_live_wait_mean':ratio(counter['live_wait_sum'],counter['purchased']),
            'by_species':{k:{**v,'D':ratio(v['truncated_wait_sum'],v['purchased'])} for k,v in species.items()},
            'products':{k:{**v,'realized_sale_mean_price':ratio(v['sell_cash'],v['sell'])} for k,v in products.items()},
            'denominators':raw_denominators,'plant_first_water_ratio':ratio(loss['planting_day_watered'],loss['plantings_all']),
            'plant_death_per_planting':ratio(loss['plant_eod_drought_deaths'],loss['plantings_all']),
            'plant_death_per_plant_eod':ratio(loss['plant_eod_drought_deaths'],loss['plant_eod_exposures']),
            'animal_escape_per_placed':ratio(loss['animal_eod_escapes'],loss['animal_placed']),
            'animal_escape_per_animal_eod':ratio(loss['animal_eod_escapes'],loss['animal_eod_exposures']),
            'overflow_qty':dict(overflow),'action_validity_counts':dict(invalid),'confirmed_invalid_rate':ratio(invalid['numerator_confirmed_invalid'],invalid['denominator']),
            'terminal_liquidation_individual_status_counts':dict(closing),
            'mean_own_cash':statistics.mean(r['own_cash'] for r in rows),'mean_opponent_cash':statistics.mean(r['opponent_cash'] for r in rows),
            'mean_margin':statistics.mean(r['margin'] for r in rows)}

def main():
    out=HERE/'assessment';out.mkdir(exist_ok=True);assert not (out/'manifest.json').exists();sources={};issues=[]
    def load(p):sources[str(p.resolve())]=sha(p);return json.loads(p.read_text())
    protocol=load(HERE.parent/'development_protocol.json');assert protocol['source_sha256']=='ea57c77215d6728e64a3c46c5cf1c2b21f2efa72d12dbb53240b544e27500e7f'
    assert set(protocol['fresh_development_seeds'])==SEEDS
    replay=load(HERE/'all_24_saved_traces/manifest.json');rv=load(HERE/'all_24_saved_traces/validation.json');assert rv['verified_games']==24 and rv['saved_actions_replayed']==24*719
    latency=load(HERE/'all_24_latency/results.json');lv=load(HERE/'all_24_latency/validation.json');assert lv['input_files_unchanged'] is True
    for f,digest in lv['files'].items():assert sha(HERE/'all_24_latency'/f)==digest
    strength=load(HERE.parent/'fresh_strength_assessment/assessment.json');assert strength['data_integrity_pass'] is True and strength['observed_unique_cells']==36
    helper=ROOT/'evaluation/summarize_g1.py';helper_sha='fe4ebdfebd652a93e0847d5330355f1280a5fcf91db4239f65bc57734dcf2399';assert sha(helper)==helper_sha;sources[str(helper)]=helper_sha
    spec=importlib.util.spec_from_file_location('frozen_g1_readonly_companions',helper);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    rows=[];seen=set()
    for job in replay['jobs']:
        run=Path(job['run_dir']);version='R7' if run.name.startswith('v125-r7_') else 'R6';opp='V120' if '_v120_' in run.name else 'PASS'
        key=(version,opp,job['seed'],job['seat']);assert key not in seen;seen.add(key)
        gp=run/'games.jsonl';sources[str(gp)]=sha(gp);g=json.loads(gp.read_text().splitlines()[job['game_index']]);m=load(run/'run_manifest.json');audit=Path(job['output']);a=load(audit/'analysis.json');own=a['seats'][g['candidate_seat']]
        assert g['key']==job['source_key']==a['source_game_key']
        lt=next(z for z in latency if z['source_game_key']==g['key']);l=lt['seats'][g['candidate_seat']]
        for issue in l['issues']:
            if issue['code']!='ZERO_PURCHASE_DENOMINATOR':issues.append({'source_key':g['key'],**issue})
        for species,z in l['by_animal'].items():
            if not all(z['checks'].values()) or z['initial_in_transit']!=0:issues.append({'source_key':g['key'],'code':'SPECIES_RECONCILIATION_OR_INITIAL_STOCK','species':species})
        metrics=h.game_metrics(g,m,run,audit)
        r={'version':version,'opponent':opp,'seed':g['seed'],'seat':g['candidate_seat'],'source_key':g['key'],'audit_dir':str(audit),
           'latency':{'status':l['status'],'issues':l['issues'],'total':l['total'],'by_animal':l['by_animal']},'denominators':own['denominators'],'actual_flow':own['actual_flow'],
           'overflow':{k:v for k,v in own['overflow'].items() if k!='first_eod_losses'},'terminal_assets':own['terminal_assets'],'companions':metrics,
           'own_cash':g['candidate_reward'],'opponent_cash':g['opponent_reward'],'margin':g['margin'],'engine_composite_sha256':g['engine_composite_sha256']}
        rows.append(r)
    assert seen=={(v,o,s,t) for v in ['R6','R7'] for o in ['PASS','V120'] for s in SEEDS for t in [0,1]}
    assert len({r['engine_composite_sha256'] for r in rows})==1
    groups=[]
    for opp in ['PASS','V120']:
        versions={v:aggregate([r for r in rows if r['version']==v and r['opponent']==opp]) for v in ['R6','R7']}
        per_seat={str(s):{v:aggregate([r for r in rows if r['version']==v and r['opponent']==opp and r['seat']==s]) for v in ['R6','R7']} for s in [0,1]}
        d6,d7=versions['R6']['D'],versions['R7']['D'];reduction=1-d7/d6 if d6 and d7 is not None else None
        nonincrease={s:(z['R7']['D']<=z['R6']['D']) if z['R7']['D'] is not None and z['R6']['D'] is not None else None for s,z in per_seat.items()}
        numeric_pass=None if reduction is None or any(x is None for x in nonincrease.values()) else reduction>=.2 and all(nonincrease.values())
        pairs=[]
        for seed in sorted(SEEDS):
            for seat in [0,1]:
                x,y=[next(r for r in rows if r['version']==v and r['opponent']==opp and r['seed']==seed and r['seat']==seat) for v in ['R6','R7']]
                pairs.append({'seed':seed,'seat':seat,'R6_purchase_count':x['latency']['total']['purchased'],'R7_purchase_count':y['latency']['total']['purchased'],
                              'R6_wait_sum':x['latency']['total']['truncated_wait']['sum'],'R7_wait_sum':y['latency']['total']['truncated_wait']['sum'],
                              'R6_D':x['latency']['total']['truncated_wait']['mean'],'R7_D':y['latency']['total']['truncated_wait']['mean'],
                              'own_cash_delta':y['own_cash']-x['own_cash'],'opponent_cash_delta':y['opponent_cash']-x['opponent_cash'],'margin_delta':y['margin']-x['margin']})
        groups.append({'opponent':opp,'versions':versions,'per_seat':per_seat,'relative_D_reduction':reduction,'per_seat_nonincrease':nonincrease,'primary_mechanism_numeric_threshold_pass':numeric_pass,'pairs':pairs})
    for path,digest in replay['sources'].items():assert sha(path)==digest;sources[path]=digest
    assert all(sha(p)==d for p,d in sources.items())
    report={'scope':'PREDECLARED_DEVELOPMENT_PRIMARY_METRIC_ONLY_NOT_G1_G2_GOLD','statistic':'D=Σ每采购动物截断等待/Σ真实采购数；按每个对手块合双席，另以各席原分子/分母核不增加。不是单局均值的平均。',
            'zero_purchase_policy':'保留所有零采购局，逐局D=null；向组贡献0/0，组或席位总分母0时PENDING；不新增每局必须采购要求。',
            'data_integrity_pass':not issues,'issues':issues,'groups':groups,'per_game':rows,
            'primary_mechanism_numeric_threshold_pass':not issues and all(g['primary_mechanism_numeric_threshold_pass'] is True for g in groups),
            'development_strength_guard_pass':strength['development_strength_guard_pass'],'causal_mechanism_qualification':'NOT_ESTABLISHED_COMPOSITION_AND_PURCHASE_COUNTS_CHANGED_NO_ABLATION',
            'candidate_calls':0,'new_independent_matches':0,'this_aggregator_engine_steps':0,'preceding_official_saved_action_replay_steps':24*719,
            'formal_G1_G2_Gold_decision':'NOT_ASSESSED'}
    dump(out/'manifest.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(__file__),'sources':sources,'summarize_g1_sha256':helper_sha,
                             'candidate_calls':0,'engine_steps':0,'new_independent_matches':0})
    dump(out/'assessment.json',report);dump(out/'validation.json',{'source_files_unchanged':True,'all_24_planned_keys_unique':True,'actual_fifo_reconciliation_pass':not issues,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0})
    print(json.dumps({'primary_mechanism_numeric_threshold_pass':report['primary_mechanism_numeric_threshold_pass'],'development_strength_guard_pass':report['development_strength_guard_pass'],
                      'groups':[{'opponent':g['opponent'],'R6':g['versions']['R6']['totals'],'R7':g['versions']['R7']['totals'],'D_R6':g['versions']['R6']['D'],'D_R7':g['versions']['R7']['D'],'relative_D_reduction':g['relative_D_reduction'],'per_seat_nonincrease':g['per_seat_nonincrease']} for g in groups]},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
