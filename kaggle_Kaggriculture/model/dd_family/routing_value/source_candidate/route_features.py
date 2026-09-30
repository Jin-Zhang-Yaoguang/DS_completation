"""Day-start observable workload for replay-supervised daily crew size."""
import numpy as np
import action_space as A, task_features as F, rules

def encode(obs):
    common,_=F.common(obs);state=F.production_state(obs);day=int(obs['step'])//24
    animal=[];crop=[]
    for y,row in enumerate(A.own_farm(obs)['tiles']):
        for x,tile in enumerate(row):
            if not isinstance(tile,dict):continue
            kind='animal' if tile.get('animal') else 'crop' if tile.get('crop') else None
            if kind is None:continue
            v=state[y*10+x];home=min(abs(x-a)+abs(y-b) for a,b in A.SHED_ACCESS)
            mature=kind=='animal' or day>=tile['planted_day']+rules.CROPS[tile['crop']]['first_yield_day']
            harvest=mature and tile.get('yield_units',0)>0
            (animal if kind=='animal' else crop).append([1,v[10],v[11],harvest,v[8] if mature else 0,home,home,v[6]])
    totals=[]
    for rows in [animal,crop]:
        a=np.asarray(rows,np.float32).reshape(-1,8);v=a.sum(0)
        if len(a):v[6]=a[:,6].max()
        totals.extend(v)
    return np.concatenate([common,F.maintenance_summary(obs,state),totals]).astype(np.float32)
