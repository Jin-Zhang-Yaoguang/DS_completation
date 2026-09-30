"""Validate constrained joint requests against actual official pre-market states."""
from pathlib import Path
import concurrent.futures,contextlib,copy,gzip,hashlib,importlib,io,json,sys
B=Path(__file__).resolve().parent
def run(task):
    version,seed=task;d=B/version
    with gzip.open(d/f'runs/development01/games/y68v_{seed}_0.json.gz','rt') as f:saved=json.load(f)
    sys.path.insert(0,str(d));import rules
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
        eng=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
    op=next(r for r in json.loads((B/'protocol.json').read_text())['opponents'] if r['name']=='y68v');p=B/op['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==op['sha256'];other=get_last_callable(p.read_text(),path=str(p));env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2)
    original=eng._process_market;expected=[None];now=[0];matches=[0];max_units=0
    def market(state,environment):
        actual=state[0].observation
        assert actual.farms[0]==expected[0]['farms'][0],(version,seed,now[0],'unit farm shadow differs')
        assert actual.private==expected[0]['private'],(version,seed,now[0],'unit resources shadow differs')
        matches[0]+=1;return original(state,environment)
    eng._process_market=market
    try:
        for t in range(719):
            now[0]=t;obs=copy.deepcopy(env.state[0].observation);obs.update(step=t,player=0);action=saved['trace'][t]['action'];orders=[action['farmer'],*action['hands']];max_units=max(max_units,len(orders));assert len(orders)<=16
            for crop in rules.CROPS:assert sum(a==['PLANT',crop] for a in orders)<=obs['private']['seeds'].get(crop,0),(seed,t,crop,'atomic oversubscription')
            assert len(orders)+sum(a[0]=='HIRE' for a in action['market'])<=16,(seed,t,'capacity reservations')
            expected[0]=copy.deepcopy(obs)
            for i,a in enumerate(orders):rules._apply_unit_action(expected[0]['farms'][0],expected[0]['private'],i,a,10,t//24,24,100)
            otherobs=copy.deepcopy(env.state[1].observation);otherobs['step']=t;env.step([action,other(otherobs)]);assert env.state[0].observation.farms[0]['money']==saved['trace'][t]['cash']
    finally:eng._process_market=original
    assert [float(s.reward) for s in env.state]==[saved['own_cash'],saved['opponent_cash']]
    return {'version':version,'seed':seed,'seat':0,'exact_pre_market_unit_farm_and_resources':matches[0],'all_atomic_plant_budgets_satisfied':True,'all_hire_capacity_reservations_satisfied':True,'max_units':max_units,'exact_saved_cash_and_final_rewards':True}
if __name__=='__main__':
    version=sys.argv[1] if len(sys.argv)>1 else 'ddbx'
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,[(version,s) for s in range(919260010,919260014)]))
    (B/'diagnostics'/f'{version}_joint_resource_audit.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
