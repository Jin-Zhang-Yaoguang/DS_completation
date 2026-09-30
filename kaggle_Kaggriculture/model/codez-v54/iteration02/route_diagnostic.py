"""Whole-route counterfactual diagnostic against fixed replay actions; not competitive evidence."""
import sys,json,hashlib,concurrent.futures,traceback,time,gc
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import research
from research_official import OfficialGame
ROOT=Path(__file__).resolve().parent
ROUTES=[0,1,3,5,7,9,100,101,103,107,110,112,115,118,120,123,126,128]
def one(job):
    start=time.monotonic();out={'job':job,'status':'error','scope':'fixed opponent tape; development diagnosis only'}
    try:
        tape=json.loads((ROOT/'tapes'/f'{job["episode_id"]}.json').read_text());seat=tape['seat'];rid=job['route']
        fn,ns=research.load(research.ROOT/'versions/v003/main.py');chassis=ns['_IMPL'].chassis;old=chassis.router;changes=[]
        assert rid in chassis.routes
        def router(obs,step,state):
            first=not state.get('day6');prior=old(obs,step,state)
            if step==144 and first:
                state['route']=rid;changes.append({'step':step,'prior':prior,'new':rid,'rkey':state.get('rkey'),'shops':obs['town']['unlocked_shops']});return rid
            return prior
        chassis.router=router;game=OfficialGame(tape['seed'])
        for recorded in tape['actions']:
            acts=list(recorded);acts[seat]=fn(game.observe(seat));game.step(*acts)
        assert game.done and len(changes)==1
        scores=[game.reward(i) for i in [0,1]]
        out.update(status='ok',scores=scores,margin=scores[seat]-scores[1-seat],route_change=changes[0])
    except Exception:out['error']=traceback.format_exc()
    out['elapsed_seconds']=time.monotonic()-start;gc.collect();return out
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=3);a=ap.parse_args()
    manifest=ROOT/'route_diagnostic_manifest.json'
    if not manifest.exists():
        rows=json.loads((ROOT/'replay_diagnosis.json').read_text())['episodes'];worst=sorted([r for r in rows if r['live_margin']<0],key=lambda r:r['v005_tape_margin'])[:8]
        jobs=[{'episode_id':r['episode_id'],'route':rid} for r in worst for rid in ROUTES]
        files=['iteration02/route_diagnostic.py','research.py','research_official.py','versions/v003/main.py']+[f'iteration02/tapes/{r["episode_id"]}.json' for r in worst]
        manifest.write_text(json.dumps({'purpose':'Locate route-ceiling vs micro-execution failures; source is borrowed r14','jobs':jobs,'hashes':{f:research.digest(research.ROOT/f) for f in files}},indent=2))
    spec=json.loads(manifest.read_text())
    for f,h in spec['hashes'].items():assert research.digest(research.ROOT/f)==h
    dest=ROOT/'route_diagnostic.jsonl';done={}
    if dest.exists():
        for s in dest.read_text().splitlines():
            r=json.loads(s);k=json.dumps(r['job'],sort_keys=True);assert k not in done;done[k]=r
    todo=[j for j in spec['jobs'] if json.dumps(j,sort_keys=True) not in done]
    with dest.open('a') as f,concurrent.futures.ProcessPoolExecutor(a.workers) as ex:
        for r in ex.map(one,todo):
            f.write(json.dumps(r)+'\n');f.flush();done[json.dumps(r['job'],sort_keys=True)]=r
            if r['status']!='ok':print(r['error'][-1500:],flush=True)
            if len(done)%18==0:print('route diagnosis',len(done),'/',len(spec['jobs']),flush=True)
    (ROOT/'route_diagnostic.summary.json').write_text(json.dumps({'complete':len(done)==len(spec['jobs']),'errors':sum(r['status']!='ok' for r in done.values()),'result_sha256':research.digest(dest)},indent=2))
