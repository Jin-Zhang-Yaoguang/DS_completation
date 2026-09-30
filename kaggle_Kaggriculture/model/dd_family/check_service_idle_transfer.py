"""Verify the idle-service intervention transfers to the atomic service executor."""
from pathlib import Path
import copy,hashlib,importlib.util,json,sys
import numpy as np
B=Path(__file__).resolve().parent;D=B/'ddbs';sys.path.insert(0,str(D))
import action_space as A,task_features as F,rules,idle_services as I,tree_runtime
def main():
    row=json.loads((B/'ddbo/source_manifest.json').read_text())['rows'][0];raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];rep=json.loads(raw);s=row['seat'];obs=copy.deepcopy(rep['steps'][0][0]['observation']);obs.update(copy.deepcopy(rep['steps'][0][s]['observation']));obs.update(player=s,step=0)
    farm=A.own_farm(obs);rules._set_farmer_position(farm,0,(4,4));farm['tiles'][3][4]=rules._new_animal('COW',0);obs['private']['shed']={'WHEAT':10};obs['private']['inventories'][0]={}
    g=np.asarray([[4,4,0],[4,3,A.UNIT_INDEX['FEED']],[4,3,A.UNIT_INDEX['CARE']],[4,2,A.UNIT_INDEX['PLANT:WHEAT']]],np.int16)
    assert len(I.alternatives(obs,0,g,{}))==0 # Atomic executor cannot fetch wheat.
    obs['private']['inventories'][0]['WHEAT']=1;assert I.alternatives(obs,0,g,{}).tolist()==[1]
    assert len(I.alternatives(obs,0,g,{1:(4,3,A.UNIT_INDEX['FEED'],1)}))==0
    obs['step']=23;assert len(I.alternatives(obs,0,g,{}))==0
    obs['step']=0;farm['tiles'][3][4]['fed_today']=True;assert I.alternatives(obs,0,g,{}).tolist()==[2]
    obs['step']=28*24;assert len(I.alternatives(obs,0,g,{}))==0
    obs['step']=29*24;assert len(I.alternatives(obs,0,g,{}))==0
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.glob('*.npz')};assert hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (B/'ddbj').glob('*.npz')}
    spec=importlib.util.spec_from_file_location('dense',B/'ddbj/tree_runtime.py');dense=importlib.util.module_from_spec(spec);spec.loader.exec_module(dense)
    path=next((B/'task_policy_data/ddbj').glob('validation_*.npz'));checks=[]
    with np.load(path) as z:
        inputs={'goal_rank':z['validation_x'][:2048],'goal_quantity':z['quantity_x'][:2048],'market_policy':z['market_x'][:2048],'market_quantity':np.concatenate([z['market_x'][:2048],F.MHOT[z['market_y'][:2048]]],axis=1)}
        for name,x in inputs.items():
            old=dense.Model(B/'ddbj'/f'{name}.npz');new=tree_runtime.Model(D/f'{name}.npz')
            for n in [1,63,64,len(x)]:assert np.array_equal(old.predict(x[:n]),new.predict(x[:n]))
            checks.append({'name':name,'rows':len(x),'bitwise_equal':True})
    report={'version':'ddbs','checks_passed':True,'atomic_feed_requires_held_material':True,'existing_service_horizon_reservation_care_terminal_passed':True,'weights_unchanged':True,'runtime_equivalence':checks,'weight_hashes':hashes}
    (B/'diagnostics/ddbs_idle_checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
