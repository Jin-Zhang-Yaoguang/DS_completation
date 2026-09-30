"""Fail-closed paired evaluation; bootstrap resamples seeds, never individual seats."""
import json,hashlib,collections
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def read_run(name):
    p=ROOT/'runs'/f'{name}.json';spec=json.loads(p.read_text());rows=[json.loads(s) for s in p.with_suffix('.jsonl').read_text().splitlines()]
    key=lambda j:json.dumps(j,sort_keys=True)
    expected=[key(j) for j in spec['jobs']];actual=[key(r['job']) for r in rows]
    assert len(set(expected))==len(expected) and len(set(actual))==len(actual)
    assert set(expected)==set(actual),'incomplete panel'
    assert all(r['status']=='ok' for r in rows),'error rows cannot be excluded'
    for path,sha in spec['hashes'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,path
    return rows

def stats(rows):
    vals=[r['margin'] for r in rows]
    return dict(n=len(vals),wins=sum(v>0 for v in vals),ties=sum(v==0 for v in vals),losses=sum(v<0 for v in vals),win_rate=sum(v>0 for v in vals)/len(vals),mean_margin=float(np.mean(vals)),max_action_seconds=max(r['max_action_seconds'] for r in rows))

def cluster_ci(rows):
    grouped=collections.defaultdict(list)
    for r in rows:grouped[r['job']['seed']].append(r['margin'])
    means=np.array([np.mean(v) for _,v in sorted(grouped.items())]);rng=np.random.default_rng(947130)
    boot=rng.choice(means,(20000,len(means)),replace=True).mean(axis=1)
    return dict(seeds=len(means),mean=float(means.mean()),lower95=float(np.quantile(boot,.025)),upper95=float(np.quantile(boot,.975)))

def evaluate(name,candidate='v005'):
    rows=read_run(name);out={'panel':name,'candidate':candidate,'scope':'official engine; both opponents run adaptive programs','versions':{}}
    for v in sorted({r['job']['agent'].split('/')[1] for r in rows}):
        group=[r for r in rows if r['job']['agent']==f'versions/{v}/main.py']
        out['versions'][v]={'overall':stats(group),'opponents':{o:stats([r for r in group if r['job']['opponent']==o]) for o in sorted({r['job']['opponent'] for r in group})}}
    cand=[r for r in rows if r['job']['agent']==f'versions/{candidate}/main.py'];r14=[r for r in cand if r['job']['opponent']=='v54r14']
    if r14:out['r14_cluster_margin']=cluster_ci(r14)
    if {'v002','v003',candidate}<=set(out['versions']):
        c=out['versions'][candidate];delta=100*(c['overall']['win_rate']-out['versions']['v002']['overall']['win_rate'])
        out['modern_bar']={'win_rate_70pct':c['overall']['win_rate']>=.7,'improvement_over_v002_20pp':delta>=20,'improvement_pp':delta,'r14_win_rate_65pct':c['opponents']['v54r14']['win_rate']>=.65,'r14_seed_cluster_lower95_positive':out['r14_cluster_margin']['lower95']>0,'no_errors':True}
        out['modern_bar_pass']=all(v for k,v in out['modern_bar'].items() if k!='improvement_pp')
    path=ROOT/'runs'/f'{name}.evaluation.json';assert not path.exists();path.write_text(json.dumps(out,indent=2));return out
if __name__=='__main__':
    import sys
    print(json.dumps(evaluate(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else 'v005'),indent=2))
