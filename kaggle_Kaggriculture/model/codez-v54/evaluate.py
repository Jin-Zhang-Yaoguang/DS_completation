"""Exact-key paired evaluation: never silently intersect missing games."""
import collections
import json
import math
from pathlib import Path
from research import ROOT, digest

def rows(name):
    p=ROOT/'runs'/f'{name}.jsonl'
    data=[json.loads(s) for s in p.read_text().splitlines()]
    spec=json.loads(p.with_suffix('.json').read_text())
    assert len(data)==len(spec['jobs']) and all(x['status']=='ok' for x in data)
    assert len({x['key'] for x in data})==len(data)
    return data

def pair(data, candidate):
    def index(agent):
        out={}
        for r in data:
            j=r['job']
            if j['agent']!=agent:continue
            k=(j['opponent'],j['seed'],j['seat'])
            if k in out:raise ValueError('duplicate pair key')
            out[k]=r
        return out
    a=index('versions/v000/main.py');b=index(candidate)
    assert a and set(a)==set(b), 'Missing paired cases'
    groups=collections.defaultdict(lambda:{'n':0,'baseline_wins':0,'candidate_wins':0,'margin_delta':0.0})
    up=down=0; baseline_ties=candidate_ties=0;changes=0; pairs=[]
    for k,x in a.items():
        y=b[k];am=x['margin'];bm=y['margin'];aw=am>0;bw=bm>0
        assert x['observations']['144']['shops'][:2]==y['observations']['144']['shops'][:2]
        up+=int(not aw and bw);down+=int(aw and not bw)
        baseline_ties+=am==0;candidate_ties+=bm==0
        changes+=y['telemetry'].get('route_changes',0)
        for group in ('all',f'opponent:{k[0]}',f'seat:{k[2]}',f'{k[0]}:seat{k[2]}'):
            g=groups[group];g['n']+=1;g['baseline_wins']+=aw;g['candidate_wins']+=bw;g['margin_delta']+=bm-am
        pairs.append({'opponent':k[0],'seed':k[1],'seat':k[2],'baseline_margin':am,'candidate_margin':bm,
            'baseline_trace':x['trace_sha256'],'candidate_trace':y['trace_sha256'],
            'triggered':y['telemetry'].get('route_changes',0)})
    discordant=up+down
    p=sum(math.comb(discordant,k) for k in range(up,discordant+1))/2**discordant if discordant else 1.0
    ok=all(g['candidate_wins']>=g['baseline_wins'] for g in groups.values())
    allg=groups['all']; ok &= allg['candidate_wins']>allg['baseline_wins'] and allg['margin_delta']>0
    return {'candidate':candidate,'groups':dict(groups),'up':up,'down':down,'one_sided_discordant_p':p,
        'baseline_ties':baseline_ties,'candidate_ties':candidate_ties,'route_changes':changes,
        'paired_gate':ok,'pairs':pairs}

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('name');a=ap.parse_args()
    data=rows(a.name)
    versions=sorted({r['job']['agent'] for r in data}-{'versions/v000/main.py'})
    reports=[pair(data,v) for v in versions]
    path=ROOT/'runs'/f'{a.name}.evaluation.json'
    if path.exists():raise FileExistsError(path)
    path.write_text(json.dumps(reports,indent=2))
    for r in reports:
        print(r['candidate'],r['groups']['all'],'up/down',r['up'],r['down'],'p',round(r['one_sided_discordant_p'],6),'strict_improvement_gate',r['paired_gate'])
