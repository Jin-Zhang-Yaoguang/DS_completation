"""Read-only source reproduction and explicit fixed-request counterfactual diagnosis."""
import concurrent.futures
import copy
import hashlib
import json
import sys
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'iteration02')]
import research
from research_official import OfficialGame


def one(mode):
    tape = json.loads((P/'tapes/112462673.json').read_text())
    version = 'v021' if mode == 'force_modern' else mode
    fn, ns = research.load(ROOT/f'versions/{version}/main.py')
    game = OfficialGame(tape['seed'])
    routes, choices, checkpoints = [], [], []
    hooked = set()
    def hook(scope, space):
        chassis = space['_IMPL'].chassis
        if id(chassis) in hooked: return
        hooked.add(id(chassis)); old = chassis.router
        def router(obs, step, state):
            prior = state.get('route'); result = old(obs, step, state)
            if prior != state.get('route') or step in [2, 144, 216]:
                routes.append(dict(scope=scope, step=step, prior=prior, result=result,
                    state_route=state.get('route'), rkey=state.get('rkey'), shops=obs['town']['unlocked_shops']))
            return result
        chassis.router = router
    hook('modern' if version=='v021' else version, ns)
    changes, first_change = 0, None
    last_choice = None
    for step, recorded in enumerate(tape['actions']):
        if mode=='force_modern' and step==2: ns['_CODEZHYBRID_CHOICE']='modern'
        obs = game.observe(0)
        action = fn(obs)
        if version=='v021':
            hook('legacy', ns['_CODEZHYBRID_BASE_NS'])
            choice = ns['_CODEZHYBRID_CHOICE']
            if choice != last_choice:
                choices.append(dict(step=step, choice=choice, rival_cash=obs['farms'][1]['money'], wheat=obs['market']['inventory']['WHEAT']))
                last_choice=choice
        if action!=recorded[0]:
            changes+=1
            if first_change is None: first_change=step
        game.step(action, recorded[1])
        if step%24==23 or step==718:
            now=game.observe(0)
            checkpoints.append(dict(step=step+1,cash=[f['money'] for f in now['farms']],shops=now['town']['unlocked_shops']))
    assert game.done
    scores=[game.reward(i) for i in (0,1)]
    if mode=='v021': assert changes==0 and scores==tape['rewards'], (changes,scores)
    return dict(mode=mode, source_sha256=research.digest(ROOT/f'versions/{version}/main.py'),
        scores=scores, margin=scores[0]-scores[1],changed_requests=changes,first_changed_step=first_change,
        expert_choices=choices,routes=routes,checkpoints=checkpoints,telemetry=ns.get('_CODEZ_STATS',{}),
        scope='Source reproduction' if mode=='v021' else 'Counterfactual vs fixed rival requests; no adaptive opponent response')


def ledger():
    import replay_ledger
    replay_ledger.ROOT=P
    r=replay_ledger.one(112462673)
    assert r['status']=='ok',r
    (P/'actual_cash_ledger.json').write_text(json.dumps(r,indent=2))
    pairs={}
    for row in r['ledger']:
        key=(row['operation'],row['item'])
        value=pairs.setdefault(key,[[0,0],[0,0]])[row['player']]
        value[0]+=row['executed_units'];value[1]+=row['cash_change']
    out=[dict(operation=k[0],item=k[1],own_units=v[0][0],rival_units=v[1][0],own_cash=v[0][1],rival_cash=v[1][1],cash_difference=v[0][1]-v[1][1]) for k,v in pairs.items()]
    out.sort(key=lambda x:x['cash_difference'])
    assert sum(x['cash_difference'] for x in out)==-17936
    (P/'cash_attribution.json').write_text(json.dumps(out,indent=2))
    print('ledger reconciled',json.dumps(out),flush=True)


if __name__=='__main__':
    files=['versions/v021/main.py','versions/v002/main.py','versions/v003/main.py','research.py','research_official.py','iteration02/replay_ledger.py']
    manifest=dict(files={f:research.digest(ROOT/f) for f in files},replay_sha256=research.digest(P/'episode-112462673-replay.json'),runner_sha256=research.digest(Path(__file__)),episode_id=112462673,submission_id=56492983,opponent_submission_id=56486364)
    (P/'manifest.json').write_text(json.dumps(manifest,indent=2))
    with concurrent.futures.ProcessPoolExecutor(4) as pool:
        future=pool.submit(ledger)
        results=list(pool.map(one,['v021','v002','v003','force_modern']))
        future.result()
    (P/'source_and_expert_ablation.json').write_text(json.dumps(results,indent=2))
    for r in results: print(json.dumps({k:v for k,v in r.items() if k!='checkpoints'}),flush=True)
