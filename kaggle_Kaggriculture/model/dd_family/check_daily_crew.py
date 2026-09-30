"""Check staffing intervention order, affordability, day boundary and exact export runtime."""
from pathlib import Path
import collections,copy,hashlib,importlib.util,json,sys
import numpy as np
B=Path(__file__).resolve().parent;D=B/'ddbq';sys.path.insert(0,str(D))
import action_space as A,task_features as F,rules,crew_features as C,tree_runtime
from main import Agent

class Constant:
    def __init__(self,value):self.value=value
    def predict(self,x):return np.full(len(x),self.value)
class Stop:
    a={'classes':np.arange(F.MT)}
    def predict(self,x):
        v=np.zeros((len(x),F.MT));v[:,0]=1;return v

def agent(crew):
    a=Agent.__new__(Agent);a.rank=Constant(0);a.quantity=Constant(1);a.market=Stop();a.marketq=Constant(1);a.crew=Constant(crew);a.crew_target=0
    a.goals={};a.previous={};a.forced=set();a.day=-1;a.stats=collections.Counter();a.last={};return a

def main():
    row=json.loads((D/'source_manifest.json').read_text())['rows'][0];raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];rep=json.loads(raw);s=row['seat']
    obs=copy.deepcopy(rep['steps'][0][0]['observation']);obs.update(copy.deepcopy(rep['steps'][0][s]['observation']));obs.update(player=s,step=0)
    original=copy.deepcopy(obs);a=agent(3);orders=a.act(obs)
    assert orders['market']==[['HIRE']]*3 and orders['hands']==[] and obs==original
    shadow=copy.deepcopy(obs)
    for request in orders['market']:rules._do_hire(A.own_farm(shadow),shadow['private'],10)
    assert len(A.own_farm(shadow)['hands'])==3 and A.own_farm(shadow)['money']==2996
    # Hires act next turn, and the daily target is cached after day start.
    shadow['step']=1;a.crew=Constant(10);orders=a.act(shadow);assert orders['market']==[] and len(orders['hands'])==3 and a.crew_target==3
    for t in [23,718]:
        test=copy.deepcopy(obs);test['step']=t;assert agent(3).act(test)['market']==[]
    for cash,expected in [(0,0),(1,1),(2,2),(3,2),(4,3)]:
        test=copy.deepcopy(obs);A.own_farm(test)['money']=cash;assert len(agent(3).act(test)['market'])==expected
    # Even a large regressor output respects the existing student's 15-hand cap.
    test=copy.deepcopy(obs);a=agent(99);a.act(test);assert a.crew_target==15
    assert C.encode(obs).shape==(143,) and np.all(np.isfinite(C.encode(obs)))
    # Sparse traversal changes only compute, across all four inherited models.
    spec=importlib.util.spec_from_file_location('dense',B/'ddbo/tree_runtime.py');dense=importlib.util.module_from_spec(spec);spec.loader.exec_module(dense)
    p=next((B/'task_policy_data/ddbo').glob('validation_*.npz'));rows=[]
    with np.load(p) as z:
        inputs={'goal_rank':z['validation_x'][:2048],'goal_quantity':z['quantity_x'][:2048],'market_policy':z['market_x'][:2048],'market_quantity':np.concatenate([z['market_x'][:2048],F.MHOT[z['market_y'][:2048]]],axis=1)}
        for name,x in inputs.items():
            old=dense.Model(B/'ddbo'/f'{name}.npz');new=tree_runtime.Model(D/f'{name}.npz')
            for n in [1,63,64,len(x)]:assert np.array_equal(old.predict(x[:n]),new.predict(x[:n])),(name,n)
            rows.append({'model':name,'rows':len(x),'bitwise_equal':True})
    report={'version':'ddbq','staffing_checks_passed':True,'features':143,'runtime_equivalence':rows}
    (B/'diagnostics/ddbq_crew_checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
