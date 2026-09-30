"""ddj: supervised conditional decision trees with autoregressive market heads.
No runtime replay, prototype-state lookup, parent policy or opponent policy calls.
"""
from pathlib import Path
import copy,json
import numpy as np
import contract,action_space as space,rules
B=Path(__file__).resolve().parent

import tree_features as F
class Agent:
    def __init__(self):
        self.trees={}
        for kind,n in [('unit',16),('market',10)]:
            for i in range(n):
                with np.load(B/f'{kind}_{i}.npz') as z:self.trees[f'{kind}_{i}']={k:z[k] for k in z.files}
        self.stats={'calls':0,'invalid_units':0,'invalid_market':0};self.last={}
    def predict(self,name,x):
        tree=self.trees[name];i=0
        while tree['left'][i]>=0:
            i=int(tree['left'][i] if x[tree['feature'][i]]<=tree['threshold'][i] else tree['right'][i])
        return int(tree['label'][i])

    def act(self,obs):
        t=int(obs['step'])
        x=contract.encode(obs);common=F.common(x['global'][None],x['board'][None],x['units'][None],[t])
        shadow=copy.deepcopy(obs);s=space.seat(obs);unitcodes=np.zeros((1,16),np.float32)
        orders=[]
        for i in range(space.unit_count(obs)):
            code=self.predict(f'unit_{i}',F.local(common,x['units'][None],i)[0]) if i<16 else 0
            tok,qty=divmod(code,102)
            if not space.unit_legal_mask(shadow,i)[tok]:
                self.stats['invalid_units']+=1;tok=0
            order=space.decode_unit(shadow,i,tok,qty);orders.append(order)
            if i<16:unitcodes[0,i]=tok*102+qty
            rules._apply_unit_action(shadow['farms'][s],shadow['private'],i,order,10,t//24,24,100)
        market=[];sh=space.market_shadow(shadow)
        ms=copy.deepcopy(obs['market']);ms['params']=rules._resolve_market_params(ms.get('params'))
        prefix=np.zeros((1,20),np.float32)
        for slot in range(10):
            code=self.predict(f'market_{slot}',F.market(common,unitcodes,prefix)[0]);tok,qty=divmod(code,102)
            prefix[0,slot*2:slot*2+2]=[tok,qty]
            if tok==0:break
            order=space.apply_market_token(sh,tok,qty)
            if order is None:self.stats['invalid_market']+=1;continue
            if order[0] in ['SELL','BUY_PRODUCT']:
                op,item,q=order;done=0
                for _ in range(q):
                    price=rules.market_price(item,ms['inventory'][item]-(op=='BUY_PRODUCT'),ms['params'])
                    if not rules._commit_unit(op,item,price,shadow['farms'][s],shadow['private'],ms,100):break
                    done+=1
                sh['money']=shadow['farms'][s]['money'];sh['shed']=dict(shadow['private']['shed'])
                sh['prices']={p:rules.market_price(p,ms['inventory'][p],ms['params']) for p in space.PRODUCTS}
                if not done:continue
                order[2]=done
            else:
                shadow['farms'][s]['money']=sh['money'];shadow['private']['shed']=dict(sh['shed']);shadow['private']['seeds']=dict(sh['seeds'])
            market.append(order)
        self.stats['calls']+=1
        return {'farmer':orders[0],'hands':orders[1:],'market':market}

_AGENT=None
def agent(obs,configuration=None):
    global _AGENT
    if _AGENT is None:_AGENT=Agent()
    return _AGENT.act(obs)
