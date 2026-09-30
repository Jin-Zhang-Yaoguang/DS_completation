"""ddf: hierarchical local-action support, selected from current visible state.

This is nonparametric behavior cloning, not neural distillation. Runtime support
contains training states/actions, never episode IDs or future observations.
"""
from pathlib import Path
import copy,json
import numpy as np
import contract,action_space as space,rules
B=Path(__file__).resolve().parent

class Agent:
    def __init__(self):
        self.config=json.loads((B/'config.json').read_text())
        self.arr={p.stem:np.load(p,mmap_mode='r') for p in (B/'data').glob('*.npy')}
        self.prev=-1;self.stats={'calls':0,'switches':0,'invalid_units':0,'invalid_market':0}
        self.last={}
        self.bw=np.asarray([8]*13+[6,2,1,2,1,1,30,10],np.float32)
        self.uw=np.asarray([30,0,100,100]+[400]*12,np.float32)

    def choose(self,obs):
        t=int(obs['step']);x=contract.encode(obs)
        board=self.arr['board'][t].astype(np.float32).reshape(-1,100,21)
        delta=board-x['board'].reshape(100,21)
        cost=np.einsum('nbi,i,nbi->n',delta,self.bw,delta)*self.config['board_scale']
        delta=self.arr['units'][t].astype(np.float32)-x['units'][:,:16]
        cost+=np.einsum('nui,i,nui->n',delta,self.uw,delta)*self.config['position_scale']
        g=self.arr['global'][t].astype(np.float32);v=x['global']
        # Own cash/hire/land/unit counts; seeds and shed; visible shop sequence.
        cost+=0.5*(g[:,4]-v[4])**2
        cost+=100*((g[:,5:8]-v[5:8])**2).sum(1)
        cost+=100*((g[:,16:33]-v[16:33])**2).sum(1)
        # Original global vector: 60; contract appends 8x9 shops then seat/board summaries.
        cost+=0.5*((g[:,33:51]-v[33:51])**2).sum(1)
        cost+=2*((g[:,60:132]-v[60:132])**2).sum(1)
        if self.prev>=0:cost[self.prev]-=self.config['continuity_bonus']
        k=int(cost.argmin())
        self.stats['switches']+=self.prev>=0 and k!=self.prev
        self.prev=k;self.last={'support_index':k,'distance':float(cost[k])}
        return k

    def local_choice(self,obs,i,t,k):
        x=contract.encode(obs)['units'][i]
        lo=max(t//24*24,t-2);hi=min(719,t//24*24+24,t+3)
        ctx=self.arr['unit_context'][lo:hi,:,i].astype(np.float32)
        w=np.concatenate([self.uw,self.bw*4,np.tile(self.bw*.5,4)])
        delta=ctx-x
        dist=np.einsum('tni,i,tni->tn',delta,w,delta)
        dist+=np.abs(np.arange(lo,hi)-t)[:,None]*.15
        # Shared-plan preference is weak; actual local feasibility is mandatory.
        dist[:,k]-=.1
        tokens=self.arr['unit_tokens'][lo:hi,:,i]
        legal=np.asarray(space.unit_legal_mask(obs,i))
        dist=np.where(legal[tokens],dist,np.inf)
        tt,kk=np.unravel_index(dist.argmin(),dist.shape)
        return int(tokens[tt,kk]),int(self.arr['unit_quantities'][lo+tt,kk,i])

    def act(self,obs):
        t=int(obs['step'])
        if t==0:self.prev=-1
        k=self.choose(obs);shadow=copy.deepcopy(obs);s=space.seat(obs)
        orders=[]
        for i in range(space.unit_count(obs)):
            tok,qty=self.local_choice(shadow,i,t,k) if i<16 else (0,0)
            if not space.unit_legal_mask(shadow,i)[tok]:
                self.stats['invalid_units']+=1;tok=0
            order=space.decode_unit(shadow,i,tok,qty);orders.append(order)
            rules._apply_unit_action(shadow['farms'][s],shadow['private'],i,order,10,t//24,24,100)
        market=[];sh=space.market_shadow(shadow)
        ms=copy.deepcopy(obs['market']);ms['params']=rules._resolve_market_params(ms.get('params'))
        for tok,qty in zip(self.arr['market_tokens'][t,k],self.arr['market_quantities'][t,k]):
            tok=int(tok);qty=int(qty)
            if tok==0:break
            order=space.apply_market_token(sh,tok,qty)
            if order is None:self.stats['invalid_market']+=1;continue
            if order[0] in ['SELL','BUY_PRODUCT']:
                op,item,q=order;done=0
                for _ in range(q):
                    price=rules.market_price(item,ms['inventory'][item],ms['params'])
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
