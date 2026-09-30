"""Exercise useful-service filtering against public resource and time boundaries."""
from pathlib import Path
import copy,hashlib,json,sys
import numpy as np
B=Path(__file__).resolve().parent;D=B/'ddbr';sys.path.insert(0,str(D))
import action_space as A,task_features as F,rules,idle_services as I
def main():
    r=json.loads((D/'source_manifest.json').read_text())['rows'][0];raw=Path(r['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['sha256'];rep=json.loads(raw);s=r['seat'];obs=copy.deepcopy(rep['steps'][0][0]['observation']);obs.update(copy.deepcopy(rep['steps'][0][s]['observation']));obs.update(player=s,step=0)
    farm=A.own_farm(obs);rules._set_farmer_position(farm,0,(4,4));farm['tiles'][3][4]=rules._new_animal('COW',0);obs['private']['shed']={};obs['private']['inventories'][0]={}
    goals=np.asarray([[4,4,0],[4,3,A.UNIT_INDEX['FEED']],[4,3,A.UNIT_INDEX['CARE']],[4,3,F.GOAL_INDEX['INSTALL:COW']],[4,2,A.UNIT_INDEX['PLANT:WHEAT']]],np.int16)
    assert len(I.alternatives(obs,0,goals,{}))==0
    obs['private']['shed']['WHEAT']=1;assert I.alternatives(obs,0,goals,{}).tolist()==[1]
    assert len(I.alternatives(obs,0,goals,{1:(4,3,A.UNIT_INDEX['FEED'],1)}))==0
    obs['step']=22;assert len(I.alternatives(obs,0,goals,{}))==0
    obs['private']['inventories'][0]['WHEAT']=1;assert I.alternatives(obs,0,goals,{}).tolist()==[1]
    obs['step']=23;assert len(I.alternatives(obs,0,goals,{}))==0
    obs['step']=0;farm['tiles'][3][4]['fed_today']=True;assert I.alternatives(obs,0,goals,{}).tolist()==[2]
    # Care accrued after production has no later realization on day 28.
    obs['step']=28*24;assert len(I.alternatives(obs,0,goals,{}))==0
    obs['step']=29*24;assert len(I.alternatives(obs,0,goals,{}))==0
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.glob('*.npz')};assert hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (B/'ddbq').glob('*.npz')}
    report={'version':'ddbr','checks_passed':True,'checks':['no speculative growth','material availability','no duplicate same service','travel plus fetch and service horizon','care needs feeding and a later production','terminal fallback disabled'],'all_five_weights_unchanged':True,'weight_hashes':hashes}
    (B/'diagnostics/ddbr_idle_checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
