"""All existing route continuations from the actual V54 legacy expert; diagnostic only."""
import concurrent.futures
import json
import traceback
from pathlib import Path
from analyze import P, ROOT, research, OfficialGame


def one(route):
    out={'route':route,'status':'error'}
    try:
        tape=json.loads((P/'tapes/112462673.json').read_text())
        fn,ns=research.load(ROOT/'versions/v002/main.py')
        chassis=ns['_IMPL'].chassis;original=chassis.router;changes=[]
        def router(obs,step,state):
            first=not state.get('day6');prior=original(obs,step,state)
            if step==144 and first:
                state['route']=route;changes.append({'step':step,'prior':prior,'new':route});return route
            return prior
        chassis.router=router;game=OfficialGame(tape['seed']);changed=0
        for step,acts in enumerate(tape['actions']):
            mine=fn(game.observe(0));changed+=mine!=acts[0]
            game.step(mine,acts[1])
        scores=[game.reward(i) for i in [0,1]]
        assert game.done and len(changes)==1
        if route==121:assert scores==tape['rewards'] and changed==0
        out.update(status='ok',scores=scores,margin=scores[0]-scores[1],changed_requests=changed,
            route_change=changes[0],final_shops=game.observe(0)['town']['unlocked_shops'])
    except Exception:out['error']=traceback.format_exc()
    return out


if __name__=='__main__':
    _,ns=research.load(ROOT/'versions/v002/main.py');routes=sorted(ns['_IMPL'].chassis.routes)
    assert len(routes)==41
    spec=dict(routes=routes,scope='Fixed rival requests; replace route at t144 only and retain subsequent original controller. Not an adaptive rival test or deployable router.',hashes={f:research.digest(ROOT/f) for f in ['versions/v002/main.py','research.py','research_official.py']},runner_sha256=research.digest(Path(__file__)),replay_sha256=research.digest(P/'episode-112462673-replay.json'))
    (P/'route_scan_manifest.json').write_text(json.dumps(spec,indent=2))
    dest=P/'route_scan.jsonl';assert not dest.exists()
    results=[]
    with dest.open('w') as f,concurrent.futures.ProcessPoolExecutor(6) as pool:
        for row in pool.map(one,routes):
            f.write(json.dumps(row)+'\n');f.flush();results.append(row)
            if len(results)%10==0:print('routes',len(results),'/41',flush=True)
    assert all(r['status']=='ok' for r in results),results
    summary=dict(complete=True,tested=41,errors=0,winning_routes=[r for r in results if r['margin']>0],top10=sorted(results,key=lambda r:r['margin'],reverse=True)[:10])
    (P/'route_scan_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
