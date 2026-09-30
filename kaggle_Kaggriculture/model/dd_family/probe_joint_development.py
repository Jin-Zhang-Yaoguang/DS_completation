"""Allocate balanced development strata at the shared replay prefix boundary."""
from pathlib import Path
import concurrent.futures,contextlib,copy,hashlib,io,json,sys
B=Path(__file__).resolve().parent;OUT=B/'joint_production_ddaw'

def run(seed):
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    sys.path.insert(0,str(B/'ddam'));import main
    policy=main.Agent();op=next(r for r in json.loads((B/'protocol.json').read_text())['opponents'] if r['name']=='y68v');p=B/op['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==op['sha256'];other=get_last_callable(p.read_text(),path=str(p))
    env=make('kaggriculture',configuration={'seed':seed});env.reset(2)
    for t in range(72):
        obs=[copy.deepcopy(s.observation) for s in env.state]
        for o in obs:o['step']=t
        env.step([policy.act(obs[0]),other(obs[1])])
    obs=copy.deepcopy(env.state[0].observation);obs['step']=72
    assert len(obs['town']['unlocked_shops'])==1
    return {'seed':seed,'first_shop':obs['town']['unlocked_shops'][0],'prefix_observation_sha256':hashlib.sha256(json.dumps(obs,sort_keys=True).encode()).hexdigest()}

def main():
    OUT.mkdir(exist_ok=True);path=OUT/'seed_probe.jsonl';rows=[json.loads(l) for l in path.read_text().splitlines()] if path.exists() else [];done={r['seed'] for r in rows};pending=[s for s in range(919270001,919270129) if s not in done]
    for offset in range(0,len(pending),24):
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
            for row in pool.map(run,pending[offset:offset+24]):
                rows.append(row)
                with path.open('a') as f:f.write(json.dumps(row)+'\n')
        print('probed',len(rows),flush=True)
    strata={shop:sorted([r['seed'] for r in rows if r['first_shop']==shop]) for shop in sorted({r['first_shop'] for r in rows})}
    assert len(strata)==8 and min(map(len,strata.values()))>=5,strata
    panels={'search':[s[0] for s in strata.values()],'refine':[x for s in strata.values() for x in s[1:3]],'validation':[x for s in strata.values() for x in s[3:5]]}
    assert len(set(sum(panels.values(),[])))==40
    result={'scope':'All 128 probed seeds are development-only; first-shop-balanced panels, not natural-distribution or formal gate claims. Validation only has its shared first 72 steps inspected.','prefix_steps':72,'strata':strata,'panels':panels,'rows':rows,'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUT/'seed_panels.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(panels),flush=True)
if __name__=='__main__':main()
