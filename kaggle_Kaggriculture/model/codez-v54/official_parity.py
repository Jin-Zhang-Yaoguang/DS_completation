"""Compare all game-state fields, every step, against official 1.32.7."""
import argparse
import contextlib
import io
import json
import time
from research import ROOT, engine, load, digest

def run(agent, opponent, seed, seat, output):
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        import kaggle_environments as ke
        from kaggle_environments.agent import get_last_callable
        env=ke.make('kaggriculture',configuration={'seed':seed},debug=True)
        env.reset(2)
    assert ke.__version__=='1.32.7',ke.__version__
    assert env.info['seed']==seed
    path=ROOT/agent
    local,_=load(path)
    with contextlib.redirect_stdout(io.StringIO()):
        fn=get_last_callable(path.read_text())
    assert fn.__name__==local.__name__
    op,_=load(ROOT/'frozen/opponents'/f'{opponent}.py')
    funcs=[None,None];funcs[seat]=fn;funcs[1-seat]=op
    game=engine().Game(seed=seed)
    fields=['farms','private','market','town','day','hour','step','player']
    checks=0;steps=0;started=time.monotonic()
    while True:
        observations=[game.observe(p) for p in (0,1)]
        for p in (0,1):
            official=env.state[p].observation
            for field in fields:
                # Shared values may only be populated on player 0 in the framework state.
                val=official.get(field,env.state[0].observation.get(field))
                assert observations[p][field]==val,(steps,p,field,str(observations[p][field])[:300],str(val)[:300])
                checks+=1
        done=game.done() if callable(game.done) else game.done
        assert done==env.done,(steps,done,env.done)
        if done:break
        acts=[funcs[p](observations[p]) for p in (0,1)]
        game.step(*acts);env.step(acts);steps+=1
    scores=[float(game.reward(p)) for p in (0,1)]
    assert scores==[float(s.reward) for s in env.state]
    result={'status':'pass','agent':agent,'sha256':digest(path),'opponent':opponent,'seed':seed,
        'seat':seat,'official_version':ke.__version__,'steps':steps,'field_checks':checks,
        'scores':scores,'entry':fn.__name__,'elapsed_seconds':time.monotonic()-started}
    out=ROOT/'runs'/output
    if out.exists():raise FileExistsError(out)
    out.write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('agent');ap.add_argument('--opponent',default='v54')
    ap.add_argument('--seed',type=int,default=13055);ap.add_argument('--seat',type=int,default=0)
    ap.add_argument('--output',default='official_baseline_parity.json');a=ap.parse_args()
    run(a.agent,a.opponent,a.seed,a.seat,a.output)
