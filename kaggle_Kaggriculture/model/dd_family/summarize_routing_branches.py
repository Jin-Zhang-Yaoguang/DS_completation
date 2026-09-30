"""Paired, seed-aware summaries of routing continuations, without optimistic claims."""
from pathlib import Path
import argparse,collections,json
import numpy as np
B=Path(__file__).resolve().parent
def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');a=ap.parse_args();out=B/'routing_value'/a.run;plan=json.loads((out/'plan.json').read_text());rows=[];missing=[]
    for _,s,seat,d,m in plan['tasks']:
        p=out/f'{s}_{seat}_{d}_{m}.json'
        if p.exists():rows.append(json.loads(p.read_text()))
        else:missing.append(p.name)
    contexts=collections.defaultdict(dict)
    for r in rows:
        key=(r['seed'],r['seat'],r['day']);contexts[key][r['mode']]=r
        if r['mode']==0:assert r['neutral_continuation_exact'] and r['cash_delta']==r['margin_delta']==r['changed_action_steps']==0
    for group in contexts.values():
        first=next(iter(group.values()))
        assert all(r['features']==first['features'] and r['parent_cash']==first['parent_cash'] and r['parent_margin']==first['parent_margin'] for r in group.values())
    stats=[]
    for day in [None,*sorted({r['day'] for r in rows})]:
        for mode in sorted({r['mode'] for r in rows}):
            rs=[r for r in rows if r['mode']==mode and (day is None or r['day']==day)]
            if not rs:continue
            stats.append({'day':day,'mode':mode,'mode_name':rs[0]['mode_name'],'branches':len(rs),'seeds':len({r['seed'] for r in rs}),'mean_cash_delta':float(np.mean([r['cash_delta'] for r in rs])),'median_cash_delta':float(np.median([r['cash_delta'] for r in rs])),'mean_margin_delta':float(np.mean([r['margin_delta'] for r in rs])),'cash_positive':sum(r['cash_delta']>0 for r in rs),'margin_positive':sum(r['margin_delta']>0 for r in rs)})
    complete=[v for v in contexts.values() if set(v)=={0,1,2,3}];oracle=[]
    for g in complete:
        best=max(g,key=lambda m:g[m]['cash_delta']);base=g[0];oracle.append({'seed':base['seed'],'day':base['day'],'best_observed_cash_mode':best,'cash_delta':g[best]['cash_delta'],'margin_delta':g[best]['margin_delta']})
    loso=[]
    if not missing:
        for seed in sorted({r['seed'] for r in rows}):
            for day in sorted({r['day'] for r in rows}):
                train=[r for r in rows if r['seed']!=seed and r['day']==day]
                means={m:float(np.mean([r['margin_delta'] for r in train if r['mode']==m])) for m in range(4)}
                choice=max(means,key=means.get);held=next(r for r in rows if r['seed']==seed and r['day']==day and r['mode']==choice)
                loso.append({'held_seed':seed,'day':day,'selected_mode':choice,'train_mean_margin_delta':means[choice],'held_margin_delta':held['margin_delta'],'held_cash_delta':held['cash_delta']})
    report={'expected':len(plan['tasks']),'completed':len(rows),'missing':missing,'seed_count':len({r['seed'] for r in rows}),'paired_contexts_complete':len(complete),'stats':stats,'hindsight_upper_bound_not_policy':oracle,'leave_one_seed_out_day_priority':loso,'warning':'Repeated branch-days from four development seeds are not independent games. Hindsight best mode is not deployable or held-out performance. LOSO averages one-day branches, not combined-policy full matches.'}
    (out/'paired_summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['missing','hindsight_upper_bound_not_policy']},indent=2))
if __name__=='__main__':main()
