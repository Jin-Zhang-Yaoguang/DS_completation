"""Current public-state features and joint feasible transport-group projection."""
import itertools
import numpy as np
import action_space as space,features

def state_features(obs):
    encoded=features.encode_observation(obs)
    bags=np.asarray([sum(b.get(item,0) for b in obs['private']['inventories'])/100 for item in space.ITEMS],np.float32)
    return np.concatenate([encoded['global'],encoded['board'].mean(axis=(1,2)).ravel(),bags]).astype(np.float32)

def project(groups,desired,budget):
    options=[list(dict.fromkeys([kind,g['original']])) for g,kind in zip(groups,desired)]
    best=None
    for selected in itertools.product(*options):
        cost=sum((space.ANIMAL_COST[k]-space.ANIMAL_COST[g['original']])*g['count'] for g,k in zip(groups,selected))
        if cost>budget:continue
        missed=sum(g['count'] for g,k,wanted in zip(groups,selected,desired) if k!=wanted)
        key=(missed,cost)
        if best is None or key<best[0]:best=(key,selected,cost)
    assert best is not None
    return best[1],best[2]
