"""Learned persistent service goals, factorized quantities, and causal market policy."""
from pathlib import Path
import copy,collections
import numpy as np
import action_space as A,rules,task_features as F,tree_runtime
B=Path(__file__).resolve().parent

class Agent:
    def __init__(self):
        self.rank=tree_runtime.Model(B/'goal_rank.npz');self.quantity=tree_runtime.Model(B/'goal_quantity.npz')
        self.market=tree_runtime.Model(B/'market_policy.npz');self.marketq=tree_runtime.Model(B/'market_quantity.npz')
        self.goals={};self.previous={};self.day=-1;self.stats=collections.Counter();self.last={}
    def act(self,obs):
        t=int(obs['step']);day=t//24
        if self.day!=day:self.goals={};self.previous={};self.day=day
        shadow=copy.deepcopy(obs);s=A.seat(obs);farm=shadow['farms'][s];private=shadow['private'];orders=[]
        for i in range(A.unit_count(obs)):
            pos=A.unit_position(shadow,i);g=self.goals.get(i)
            if g:
                rules._set_farmer_position(farm,i,g[:2]);legal=A.unit_legal_mask(shadow,i)[g[2]];rules._set_farmer_position(farm,i,pos)
                if not legal:self.goals.pop(i);g=None;self.stats['cancelled_goals']+=1
            if g is None:
                candidates=F.transfer_filter(shadow,i,F.candidates(shadow,i),self.previous);x=F.goal_features(shadow,i,candidates,self.goals,self.previous)
                chosen=int(np.argmax(self.rank.predict(x)));goal=tuple(int(v) for v in candidates[chosen]);q=0
                if A.UNIT_TOKENS[goal[2]].startswith(('PICKUP:','PLACE:')):q=max(1,min(100,int(round(float(self.quantity.predict(x[chosen:chosen+1])[0])))))
                g=(*goal,q);self.stats['goal_decisions']+=1
                if g[2]:self.goals[i]=g
            x,y,tok,q=g
            if pos[0]!=x:order=['EAST' if x>pos[0] else 'WEST']
            elif pos[1]!=y:order=['SOUTH' if y>pos[1] else 'NORTH']
            else:
                order=A.decode_unit(shadow,i,tok,q)
                if tok:self.previous[i]=g[:3];self.goals.pop(i,None);self.stats['service_actions']+=1
                else:self.stats['wait_actions']+=1
            orders.append(order);rules._apply_unit_action(farm,private,i,order,10,day,24,100)
        market=[];prefix=[]
        for slot in range(10):
            x=F.market_features(shadow,slot,prefix);probs=self.market.predict(x[None,:])[0]
            legal=np.asarray([*A.market_legal_mask(A.market_shadow(shadow)),True])
            seed_cap=A.unit_count(shadow) if t<718 else 0
            for crop in A.CROPS:
                if private['seeds'].get(crop,0)>=seed_cap:legal[A.MARKET_INDEX['BUY_SEED:'+crop]]=False
            classes=self.market.a['classes'];probs=np.where(legal[classes],probs,-1)
            tok=int(classes[int(np.argmax(probs))])
            if tok==0:break
            q=0 if tok==F.WAIT_MARKET else max(1,min(100,int(round(float(self.marketq.predict(np.concatenate([x,F.MHOT[tok]])[None,:])[0])))))
            name=A.MARKET_TOKENS[tok] if tok<F.MT else 'WAIT_SLOT'
            if name.startswith('BUY_SEED:'):
                room=max(0,seed_cap-private['seeds'].get(name.split(':')[1],0))
                if q>room:self.stats['seed_quantity_clipped']+=q-room;q=room
                assert q>0
            order=F.apply_market(shadow,tok,q)
            if order is None:self.stats['market_no_fill']+=1;break
            market.append(order);actual=int(order[2]) if len(order)>2 else 1;prefix.append((tok,actual));self.stats['market_orders']+=1
        self.last={'active_goals':len(self.goals),'method':'learned_goal_ranking'}
        return {'farmer':orders[0],'hands':orders[1:],'market':market}
