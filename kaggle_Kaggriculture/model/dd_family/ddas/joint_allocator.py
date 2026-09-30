"""Joint purchase composition from current visible state and planned quantity."""
import itertools
import numpy as np
import contract,action_space as space

IDX=[0,4,16,*range(33,60)]

def features(obs,total):
    enc=contract.encode(obs)
    global_values=enc['global'].astype(np.float16).astype(np.float32)
    placed=enc['board'].reshape(100,21)[:,10:13].sum(0)/16
    private=obs['private']
    stock=np.asarray([private['shed'].get(item,0) for item in space.ANIMALS])/16
    bags=np.asarray([sum(inv.get(item,0) for inv in private['inventories']) for item in space.ANIMALS])/16
    return np.concatenate([global_values[IDX],placed,stock,bags,[total/16]]).astype(np.float32)

def predict(model,x):
    node=0
    while model['left'][node]>=0:
        node=model['left'][node] if x[model['feature'][node]]<=model['threshold'][node] else model['right'][node]
    return model['sheep_share'][node]

def project(groups,target,budget):
    """Keep original sheep and choose whole transport groups under shared cash."""
    options=[['SHEEP'] if g['original']=='SHEEP' else [g['original'],'SHEEP'] for g in groups]
    best=None
    for selected in itertools.product(*options):
        extra=sum((space.ANIMAL_COST[k]-space.ANIMAL_COST[g['original']])*g['count'] for k,g in zip(selected,groups))
        if extra>budget:continue
        sheep=sum(g['count'] for k,g in zip(selected,groups) if k=='SHEEP')
        changed=sum(g['count'] for k,g in zip(selected,groups) if k!=g['original'])
        key=(abs(sheep-target),changed,extra)
        if best is None or key<best[0]:best=(key,selected,extra)
    assert best is not None
    return best[1],best[2]
