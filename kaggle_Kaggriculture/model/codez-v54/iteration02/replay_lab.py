"""Official historical reproduction and explicitly open-loop counterfactuals."""
import concurrent.futures
import gc
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import research as core
from research_official import OfficialGame
ROOT=Path(__file__).resolve().parent

def one(job):
    start=time.monotonic();out={'job':job,'status':'error'}
    try:
        path=ROOT/'tapes'/f'{job["episode_id"]}.json';tape=json.loads(path.read_text())
        game=OfficialGame(tape['seed']);seat=tape['seat'];op=1-seat
        fn=ns=None
        if job['mode']!='historical':fn,ns=core.load(core.ROOT/job['agent'])
        changes=0;first_change=None;timeline=[];count=0
        for step,recorded in enumerate(tape['actions']):
            assert not game.done
            acts=[dict(a) for a in recorded]
            if fn is not None:
                acts[seat]=fn(game.observe(seat))
                if acts[seat]!=recorded[seat]:
                    changes+=1
                    if first_change is None:first_change=step
            game.step(*acts);count+=1
            if step%24==23 or step==718:
                ob=game.observe(seat)
                timeline.append({'step':step+1,'cash':[f['money'] for f in ob['farms']],
                    'hands':[len(f['hands']) for f in ob['farms']],
                    'shops':ob['town'].get('unlocked_shops',[])})
        assert game.done and count==719
        rewards=[float(game.reward(p)) for p in [0,1]];margin=rewards[seat]-rewards[op]
        exact=rewards==tape['rewards']
        if job['mode']=='historical':assert exact,('historical reproduction mismatch',rewards,tape['rewards'])
        out.update(status='ok',scope='historical reproduction' if fn is None else 'fixed opponent request tape; no opponent reaction',
            scores=rewards,margin=margin,live_margin=tape['live_margin'],margin_delta=margin-tape['live_margin'],
            reward_exact=exact,changed_requests=changes,first_changed_step=first_change,
            opponent=tape['opponent_name'],opponent_submission=tape['opponent_submission_id'],
            signatures=tape['observations'],timeline=timeline,source_replay_sha256=tape['replay_sha256'],
            tape_sha256=core.digest(path),telemetry=ns.get('_CODEZ_STATS',{}) if ns else {})
    except Exception:out['error']=traceback.format_exc()
    out['elapsed_seconds']=time.monotonic()-start;gc.collect();return out

def run(name,workers=6):
    manifest=ROOT/f'{name}.json';spec=json.loads(manifest.read_text())
    for p,sha in spec['hashes'].items():assert core.digest(core.ROOT/p)==sha,p
    dest=manifest.with_suffix('.jsonl');done={}
    if dest.exists():
        for line in dest.read_text().splitlines():
            x=json.loads(line);key=json.dumps(x['job'],sort_keys=True);assert key not in done;done[key]=x
    todo=[j for j in spec['jobs'] if json.dumps(j,sort_keys=True) not in done]
    print(name,'pending',len(todo),'total',len(spec['jobs']),flush=True)
    with dest.open('a') as f,concurrent.futures.ProcessPoolExecutor(workers) as ex:
        for x in ex.map(one,todo):
            f.write(json.dumps(x,ensure_ascii=False)+'\n');f.flush();done[json.dumps(x['job'],sort_keys=True)]=x
            if x['status']!='ok':print(x['error'],flush=True)
            if len(done)%10==0 or len(done)==len(spec['jobs']):print(name,len(done),'/',len(spec['jobs']),flush=True)
    assert len(done)==len(spec['jobs'])
    (ROOT/f'{name}.summary.json').write_text(json.dumps({'complete':True,'errors':sum(r['status']!='ok' for r in done.values()),'manifest_sha256':core.digest(manifest),'result_sha256':core.digest(dest)},indent=2))

def make_manifest(name,jobs):
    files={'iteration02/replay_lab.py','research.py','research_official.py'}
    files|={j['agent'] for j in jobs if 'agent' in j}
    files|={f'iteration02/tapes/{j["episode_id"]}.json' for j in jobs}
    p=ROOT/f'{name}.json'
    if p.exists():raise FileExistsError(p)
    p.write_text(json.dumps({'jobs':jobs,'hashes':{f:core.digest(core.ROOT/f) for f in files}},indent=2))

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('name');ap.add_argument('--workers',type=int,default=6)
    a=ap.parse_args();run(a.name,a.workers)
