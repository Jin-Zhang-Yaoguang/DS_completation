"""Observe actual official unit calls; distinguish no effect from missing execution."""
from pathlib import Path
import collections,contextlib,copy,gzip,hashlib,importlib,io,json,sys
B=Path(__file__).resolve().parent
def main():
    version=sys.argv[1] if len(sys.argv)>1 else 'ddbv';seed=int(sys.argv[2]) if len(sys.argv)>2 else 919260010;seat=0
    with gzip.open(B/f'{version}/runs/development01/games/y68v_{seed}_0.json.gz','rt') as f:saved=json.load(f)
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
        eng=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
    op=next(r for r in json.loads((B/'protocol.json').read_text())['opponents'] if r['name']=='y68v');p=B/op['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==op['sha256'];other=get_last_callable(p.read_text(),path=str(p))
    env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2);original=eng._apply_unit_action;calls=collections.Counter();changed=collections.Counter();requested=collections.Counter();samples=[];now=[0]
    def wrapped(farm,private,idx,action,*args,**kwargs):
        player=sys._getframe(1).f_locals['i']
        if player!=seat:return original(farm,private,idx,action,*args,**kwargs)
        before=copy.deepcopy((farm,private));r=original(farm,private,idx,action,*args,**kwargs);name=action[0];calls[name]+=1;different=before!=(farm,private);changed[name]+=different
        if not different and name not in ['PASS','NORTH','SOUTH','EAST','WEST'] and len(samples)<20:samples.append({'step':now[0],'unit':idx,'request':action,'position':eng._farmer_position(farm,idx)})
        return r
    eng._apply_unit_action=wrapped
    try:
        for t in range(719):
            now[0]=t;action=saved['trace'][t]['action'];requested.update(a[0] for a in [action['farmer'],*action['hands']]);obs=copy.deepcopy(env.state[1].observation);obs['step']=t;env.step([action,other(obs)]);assert env.state[0].observation.farms[0]['money']==saved['trace'][t]['cash']
    finally:eng._apply_unit_action=original
    assert [float(s.reward) for s in env.state]==[saved['own_cash'],saved['opponent_cash']]
    out={'version':version,'seed':seed,'seat':seat,'exact_719_cash_and_final_rewards':True,'requested':dict(requested),'official_called':dict(calls),'official_state_changed':dict(changed),'requested_but_not_called':dict(requested-calls),'no_effect_samples':samples,'meaning':'No state change includes redundant requests, not necessarily schema illegality. Counters observe the actual official unit function, including atomic interpreter filtering.'}
    (B/f'diagnostics/{version}_{seed}_actual_requests.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='no_effect_samples'},indent=2))
if __name__=='__main__':main()
