import sys,json,concurrent.futures
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import research
from research_official import official_one
P=Path(__file__).resolve().parent

def one(spec):
    load=research.load
    def hooked(path):
        fn,ns=load(path)
        if Path(path)==research.ROOT/spec['job']['agent']:ns.update(spec.get('overrides',{}))
        return fn,ns
    research.load=hooked
    try:r=official_one(spec['job'])
    finally:research.load=load
    r['overrides']=spec.get('overrides',{});return r
if __name__=='__main__':
    extended=[json.loads(s) for s in (research.ROOT/'runs/34_frozen_extended_pool.jsonl').read_text().splitlines()]
    worst=[min([r for r in extended if r['job']['agent']=='versions/v014/main.py' and r['job']['opponent']==o],key=lambda r:r['margin'])['job'] for o in ['v55','guru_v4','busya_race']]
    jobs=[{'job':{**j,'agent':f'versions/{v}/main.py'}} for j in worst for v in ['v005','v010','v015']]
    jobs.append({'job':dict(agent='versions/v003/main.py',opponent='y68h',seed=1109,seat=0,backend='official_1.32.7'),'overrides':{'V9_RACE_DEFAULT':40,'V9_RACE_MAX':48}})
    (P/'component_attribution_manifest.json').write_text(json.dumps({'jobs':jobs,'runner_sha256':research.digest(Path(__file__)),'sources':{j['job']['agent']:research.digest(research.ROOT/j['job']['agent']) for j in jobs}},indent=2))
    dest=P/'component_attribution.jsonl';assert not dest.exists()
    with dest.open('w') as f,concurrent.futures.ProcessPoolExecutor(4) as ex:
        for r in ex.map(one,jobs):
            f.write(json.dumps(r)+'\n');f.flush();print(r['job']['agent'],r['job']['opponent'],r['job']['seed'],r['status'],r.get('margin'),r.get('overrides'),flush=True)
