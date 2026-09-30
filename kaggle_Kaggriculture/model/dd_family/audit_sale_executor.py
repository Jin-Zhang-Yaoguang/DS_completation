"""Disable learned sale delays and require full baseline trajectory parity."""
from pathlib import Path
import concurrent.futures,contextlib,copy,gzip,hashlib,io,json,sys
B=Path(__file__).resolve().parent

def run(seed):
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    sys.path.insert(0,str(B/'ddat'));import main
    # Only this verification process injects a full-sale control. Candidate
    # files and submitted inference use the fitted model without this override.
    main.sale_policy.quantities=lambda obs,model:{item:100 for item in main.sale_policy.ITEMS}
    policy=main.Agent();baseline=json.load(gzip.open(B/'ddam/runs/broad01/games'/f'y68v_{seed}_0.json.gz','rt'))
    op=next(o for o in json.loads((B/'protocol.json').read_text())['opponents'] if o['name']=='y68v');path=B/op['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==op['sha256'];other=get_last_callable(path.read_text(),path=str(path))
    env=make('kaggriculture',configuration={'seed':seed});env.reset(2)
    for t in range(719):
        obs=[copy.deepcopy(s.observation) for s in env.state]
        for o in obs:o['step']=t
        action=policy.act(obs[0]);assert action==baseline['trace'][t]['action'],(seed,t,action,baseline['trace'][t]['action'])
        env.step([action,other(obs[1])]);assert env.state[0].observation.farms[0]['money']==baseline['trace'][t]['cash']
    rewards=[float(s.reward) for s in env.state];assert rewards==[baseline['own_cash'],baseline['opponent_cash']]
    return {'seed':seed,'steps':719,'exact_actions_and_cash':True,'rewards':rewards}

if __name__=='__main__':
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:rows=list(pool.map(run,[919260010,919262004]))
    (B/'audit_sale_executor.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
