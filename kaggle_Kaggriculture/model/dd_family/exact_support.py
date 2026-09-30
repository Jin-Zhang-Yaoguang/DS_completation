"""Exact own physical state; prices and money are context, never hidden identifiers."""
import copy,hashlib,json
def key(obs):
    seat=int(obs['player']);farm=copy.deepcopy(obs['farms'][seat]);farm.pop('money',None)
    private=copy.deepcopy(obs['private'])
    for field in ['shed','seeds']:private[field]={k:v for k,v in private[field].items() if v}
    private['inventories']=[{k:v for k,v in bag.items() if v} for bag in private['inventories']]
    payload={'step':int(obs['step']),'farm':farm,'private':private}
    return hashlib.blake2b(json.dumps(payload,sort_keys=True,separators=(',',':')).encode(),digest_size=16).hexdigest()
