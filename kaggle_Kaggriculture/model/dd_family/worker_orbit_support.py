"""Coverage upper bound modulo hired-worker numbering, not an executable policy.

The farmer remains distinguished. Joint actions need a separate sequential
execution-equivalence check before any future use: workers share resources.
"""
import copy, hashlib, json

def digest(value):
    return hashlib.blake2b(json.dumps(value,sort_keys=True,separators=(',',':')).encode(),digest_size=16).hexdigest()

def canonical(obs,action=None):
    farm=copy.deepcopy(obs['farms'][int(obs['player'])]);farm.pop('money',None)
    private=copy.deepcopy(obs['private'])
    for name in ['shed','seeds']:
        private[name]={k:v for k,v in private[name].items() if v}
    bags=[{k:v for k,v in bag.items() if v} for bag in private['inventories']]
    assert len(bags)==len(farm['hands'])+1
    worker_states=[json.dumps([xy,bag],sort_keys=True,separators=(',',':')) for xy,bag in zip(farm.pop('hands'),bags[1:])]
    private['inventories']=[bags[0]]
    state={'step':int(obs['step']),'farm':farm,'private':private,'workers':sorted(worker_states)}
    result=digest(state)
    if action is None:return result
    orders=list(action.get('hands',[]))
    workers=sorted((s,json.dumps(orders[i] if i<len(orders) else ['PASS'],separators=(',',':'))) for i,s in enumerate(worker_states))
    return result,digest({'farmer':action.get('farmer',['PASS']),'hands':workers,'market':action.get('market',[])})
