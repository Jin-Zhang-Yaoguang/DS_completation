"""Complete panels, paired seed-block comparisons, unchanged trajectory metric."""
from pathlib import Path
import json,gzip,statistics,hashlib,collections
import numpy as np
from trajectory_metrics import similarity
G=Path(__file__).resolve().parent;B=G.parent;PLAN=json.loads((G/'plan.json').read_text())
def compact(r):return {k:v for k,v in r.items() if k not in ['trace','plan_log','feedback_log']}
def block_comparison(left,right):
    key=lambda r:(r['opponent'],r['seed'],r['seat'])
    rs={key(r):r for r in right};ls={key(r):r for r in left};assert set(ls)==set(rs)
    out={}
    for field in ['own_cash','margin']:
        diffs=collections.defaultdict(list)
        for k,r in ls.items():diffs[r['seed']].append(r[field]-rs[k][field])
        means=np.asarray([np.mean(v) for k,v in sorted(diffs.items())]);rng=np.random.default_rng(127);boot=rng.choice(means,(5000,len(means)),replace=True).mean(axis=1)
        out[field]={'mean_paired_delta':float(means.mean()),'seed_blocks':len(means),'exploratory_seed_bootstrap_95':np.quantile(boot,[.025,.975]).tolist(),'left_mean':float(np.mean([r[field] for r in left])),'right_mean':float(np.mean([r[field] for r in right]))}
    return out

def load_panel(panel):
    if panel=='development':seeds=PLAN['development_seeds'];kinds=PLAN['development_variants'];ops=PLAN['development_opponents']
    elif panel=='gate':seeds=PLAN['gate_seeds'];kinds=PLAN['gate_variants'];ops=[o['model'] for o in PLAN['opponents']]
    else:seeds=PLAN['fresh_confirmation_seeds'];kinds=PLAN['fresh_variants'];ops=PLAN['fresh_opponents']
    expected={(k,op,s,seat) for k in kinds for op in ops for s in seeds for seat in [0,1]};found=set();rows=[]
    for path in sorted((G/panel/'games').glob('*.json.gz')):
        with gzip.open(path,'rt') as f:r=json.load(f)
        key=(r['candidate'],r['opponent'],r['seed'],r['seat']);assert key in expected and key not in found,key;found.add(key)
        assert r['statuses']==['DONE','DONE'] and r['steps']==719 and len(r['plan_log'])==30
        assert r['win']==(r['own_cash']>r['opponent_cash'])
        rows.append(r)
    assert found==expected,(panel,len(found),len(expected))
    groups=[]
    for k in kinds:
        for op in ops:
            rs=[r for r in rows if r['candidate']==k and r['opponent']==op];n=len(rs);wins=sum(r['win'] for r in rs);draws=sum(r['draw'] for r in rs)
            counters=collections.Counter()
            for r in rs:
                for fb in r.get('feedback_log',[]):counters.update(fb['deferred_reasons'])
            group={'candidate':k,'opponent':op,'games':n,'wins':wins,'draws':draws,'losses':n-wins-draws,'win_rate':wins/n,'mean_cash':statistics.mean(r['own_cash'] for r in rs),'mean_margin':statistics.mean(r['margin'] for r in rs),'escapes':sum(len(r['escapes']) for r in rs),'drought':sum(len(r['drought']) for r in rs),'day0_zero_cash':sum(r['daily'][0]['cash']==0 for r in rs),'day1_zero_hands':sum(r['daily'][1]['hands']==0 for r in rs),'max_local_step_seconds':max(r['max_step_seconds'] for r in rs),'feedback_reason_sample_counts':dict(counters),'trajectory':similarity(rs)}
            groups.append(group)
    agg={}
    for k in kinds:
        rr=[r for r in rows if r['candidate']==k];gg=[g for g in groups if g['candidate']==k]
        agg[k]={'games':len(rr),'wins':sum(r['win'] for r in rr),'draws':sum(r['draw'] for r in rr),'mean_cash':statistics.mean(r['own_cash'] for r in rr),'mean_margin':statistics.mean(r['margin'] for r in rr),'mean_escapes':statistics.mean(len(r['escapes']) for r in rr),'mean_drought':statistics.mean(len(r['drought']) for r in rr),'day0_zero_cash':sum(r['daily'][0]['cash']==0 for r in rr),'day1_zero_hands':sum(r['daily'][1]['hands']==0 for r in rr),'trajectory_consistency':statistics.mean(g['trajectory']['unit_hash']['mean'] for g in gg),'per_actor_consistency':statistics.mean(g['trajectory']['per_actor_agreement']['mean'] for g in gg),'full_action_consistency':statistics.mean(g['trajectory']['full_hash']['mean'] for g in gg),'market_consistency':statistics.mean(g['trajectory']['market_hash']['mean'] for g in gg),'daily_consistency':[statistics.mean(g['trajectory']['unit_daily_mean'][d] for g in gg) for d in range(30)]}
    comparisons={}
    if panel=='gate':
        old=[];a=B.parent/'v127a_neural_daily_tasks/gate_y68_20260915/games'
        for r in rows:
            with gzip.open(a/f"{r['opponent']}_{r['seed']}_{r['seat']}.json.gz",'rt') as f:old.append(compact(json.load(f)))
        comparisons['v127b_minus_v127a']=block_comparison(rows,old)
    else:
        for other in ['v127a','reserve_only','time_tasks']:
            if other in kinds:comparisons['v127b_minus_'+other]=block_comparison([r for r in rows if r['candidate']=='v127b'],[r for r in rows if r['candidate']==other])
    out={'panel':panel,'games':len(rows),'aggregates':agg,'groups':groups,'paired_comparisons':comparisons,'all_done':True,'gate_pass':all(g['wins']==g['games'] for g in groups) if panel=='gate' else None}
    (G/panel/'summary.json').write_text(json.dumps(out,indent=2,ensure_ascii=False));(G/panel/'games_summary.json').write_text(json.dumps([compact(r) for r in rows],ensure_ascii=False))
    print(panel,json.dumps(agg,ensure_ascii=False),flush=True)
    return out
if __name__=='__main__':
    freeze=json.loads((G/'candidate_freeze.json').read_text())
    for fn,h in freeze.items():assert hashlib.sha256((B/fn).read_bytes()).hexdigest()==h,fn
    for o in PLAN['opponents']:assert hashlib.sha256(Path(o['frozen']).read_bytes()).hexdigest()==o['sha256'],o['model']
    results={p:load_panel(p) for p in ['development','gate','fresh']}
    (G/'summary.json').write_text(json.dumps(results,indent=2,ensure_ascii=False))
