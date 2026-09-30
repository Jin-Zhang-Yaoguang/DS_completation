"""Verify fitted schedule integrates exactly with its unchanged prefix and first branch."""
from pathlib import Path
import contextlib,copy,gzip,hashlib,io,json,sys
import numpy as np
B=Path(__file__).resolve().parent;D=B/'ddbt';sys.path.insert(0,str(D))
from main import Agent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    report=json.loads((D/'value_training_report.json').read_text());assert all(sha(D/p)==h for p,h in report['hashes'].items())
    values=np.load(D/'route_values.npy');assert values.shape==(30,4);assert values.argmax(1).tolist()==[3 if d==3 else 1 if d==10 else 0 for d in range(30)]
    assert all(sha(p)==sha(B/'ddbs'/p.name) for p in D.glob('*.npz'))
    with gzip.open(B/'ddbs/runs/development01/games/y68v_919260010_0.json.gz','rt') as f:parent=json.load(f)
    branch=json.loads((B/'routing_value/priority_pilot/919260010_0_3_3.json').read_text())
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    op=next(r for r in json.loads((B/'protocol.json').read_text())['opponents'] if r['name']=='y68v');p=B/op['file'];assert sha(p)==op['sha256'];other=get_last_callable(p.read_text(),path=str(p));env=make('kaggriculture',configuration={'seed':919260010},debug=False);env.reset(2);agent=Agent()
    for t in range(96):
        obs=[copy.deepcopy(s.observation) for s in env.state]
        for o in obs:o['step']=t
        own=agent.act(obs[0]);expected=parent['trace'][t]['action'] if t<72 else branch['one_day_actions'][t-72];assert own==expected,(t,'prefix/branch integration differs')
        assert agent.route_mode==(3 if t>=72 else 0)
        env.step([own,other(obs[1])])
        if t<72:assert env.state[0].observation.farms[0]['money']==parent['trace'][t]['cash']
    result={'version':'ddbt','hashes_passed':True,'all_four_replay_models_unchanged':True,'30_day_table_checked':True,'prefix_actions_cash_exact':72,'first_intervention_actions_exact':24,'official_engine':'1.32.7'}
    (B/'diagnostics/ddbt_routing_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
