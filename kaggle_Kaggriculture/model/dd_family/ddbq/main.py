"""Distilled production options with explicit execution prerequisites and procurement pledges."""
from pathlib import Path
import copy,collections
import numpy as np
import action_space as A,rules,task_features as F,tree_runtime,production as P,maintenance as M,crew_features as C
B=Path(__file__).resolve().parent

class Agent:
    def __init__(self):
        self.rank=tree_runtime.Model(B/'goal_rank.npz');self.quantity=tree_runtime.Model(B/'goal_quantity.npz')
        self.market=tree_runtime.Model(B/'market_policy.npz');self.marketq=tree_runtime.Model(B/'market_quantity.npz')
        self.crew=tree_runtime.Model(B/'daily_crew.npz');self.crew_target=0
        self.goals={};self.previous={};self.forced=set();self.day=-1;self.stats=collections.Counter();self.last={}
    def act(self,obs):
        t=int(obs['step']);day=t//24
        if self.day!=day:
            self.stats['unfinished_at_day_change']+=len(self.goals);self.goals={};self.previous={};self.forced=set();self.day=day
            self.crew_target=max(0,min(15,int(round(float(self.crew.predict(C.encode(obs)[None,:])[0])))))
        shadow=copy.deepcopy(obs);s=A.seat(obs);farm=shadow['farms'][s];private=shadow['private'];orders=[]
        assignments=M.assign(shadow,self.goals,self.forced)
        for i in self.forced-set(assignments):self.goals.pop(i,None)
        for i,g in assignments.items():
            if self.goals.get(i)!=g:self.stats['maintenance_overrides']+=1
            self.goals[i]=g
        self.forced=set(assignments)
        for i in range(A.unit_count(obs)):
            g=self.goals.get(i)
            delivery=M.terminal_return(shadow,i)
            if delivery is not None:self.goals[i]=delivery;g=delivery;self.stats['terminal_returns']+=1
            if g and P.target_done(shadow,i,g):
                self.previous[i]=g[:3];self.goals.pop(i);g=None;self.stats['externally_completed_goals']+=1
            if g and not P.valid(shadow,i,g,self.goals):
                self.goals.pop(i);g=None;self.stats['reconciled_goals']+=1
            if g is None:
                candidates=F.transfer_filter(shadow,i,M.terminal_reachable(shadow,i,M.filter_growth(shadow,F.candidates(shadow,i,self.goals))),self.previous);x=F.goal_features(shadow,i,candidates,self.goals,self.previous)
                chosen=int(np.argmax(self.rank.predict(x)));goal=tuple(int(v) for v in candidates[chosen]);name=F.GOAL_TOKENS[goal[2]];q=1
                if name.startswith(('PICKUP:','PLACE:')) or name in ['FEED','FERTILIZE']:
                    q=max(1,min(100,int(round(float(self.quantity.predict(x[chosen:chosen+1])[0])))))
                g=(*goal,q);self.stats['goal_decisions']+=1
                if g[2]:self.goals[i]=g
            order=P.next_order(shadow,i,g);before=copy.deepcopy((farm['tiles'],private['inventories'][i],private['shed'],private['seeds']))
            orders.append(order);rules._apply_unit_action(farm,private,i,order,10,day,24,100)
            changed=before!=(farm['tiles'],private['inventories'][i],private['shed'],private['seeds']);name=F.GOAL_TOKENS[g[2]]
            if order[0]=='PASS':self.stats['wait_actions']+=1
            elif order[0] not in A.MOVES and changed:self.stats['successful_services']+=1
            done=P.target_done(shadow,i,g)
            if name.startswith('PICKUP:') and order[0]=='PICKUP' and changed:
                item=name.split(':')[1];got=private['inventories'][i].get(item,0)-before[1].get(item,0)
                if got<g[3]:self.goals[i]=(*g[:3],g[3]-got)
                else:done=True
            elif not name.startswith(('INSTALL:','PLANT:')) and order[0] not in ['PASS',*A.MOVES] and changed and order[0]==name.split(':')[0]:done=True
            if done and g[2]:self.previous[i]=g[:3];self.goals.pop(i,None);self.stats['completed_options']+=1
        market=[];prefix=[]
        for slot in range(10):
            needs,pledged=P.offers(shadow,self.goals);x=F.market_features(shadow,slot,prefix,self.goals);classes=self.market.a['classes'];probs=self.market.predict(x[None,:])[0]
            legal=np.ones(F.MT+1,bool);money_mask=A.market_legal_mask(A.market_shadow(shadow))
            if A.unit_count(shadow)>=16:legal[A.MARKET_INDEX['HIRE']]=False
            for tok,name in enumerate(A.MARKET_TOKENS):
                if name.startswith(('BUY_SEED:','BUY_PRODUCT:','BUY_ANIMAL:')) or name=='BUY_LAND':legal[tok]=day<29 and needs.get(tok,0)>0
            tok=int(classes[int(np.argmax(np.where(legal[classes],probs,-1)))]);repair=False
            possible=[k for k in needs if money_mask[k]] if day<29 else []
            if possible and (tok==0 or slot>=8):tok=possible[0];repair=True
            if tok==0 and len(farm['hands'])<self.crew_target and t%24<23 and t<718 and money_mask[A.MARKET_INDEX['HIRE']]:
                tok=A.MARKET_INDEX['HIRE'];self.stats['crew_floor_hires']+=1
            if tok==0:break
            name=A.MARKET_TOKENS[tok];q=needs[tok] if repair else max(1,min(100,int(round(float(self.marketq.predict(np.concatenate([x,F.MHOT[tok]])[None,:])[0])))))
            if name in ['HIRE','BUY_LAND']:q=1
            if name.startswith(('BUY_SEED:','BUY_PRODUCT:','BUY_ANIMAL:')):q=min(q,needs[tok])
            if name.startswith('SELL:'):
                item=name.split(':')[1]
                if item in pledged:q=min(q,max(0,private['shed'].get(item,0)-pledged[item]))
            parts=name.split(':');request=parts+[q] if len(parts)==2 else parts
            applied=F.apply_market(shadow,tok,q) if q>0 else None
            if repair:self.stats['procurement_repairs']+=1
            if applied is None:self.stats['own_shadow_unfilled_requests']+=1
            market.append(request);prefix.append((tok,q));self.stats['market_orders']+=1
        self.last={'active_goals':len(self.goals),'method':'production_options_daily_crew','crew_target':self.crew_target,'goals':{str(i):list(g) for i,g in self.goals.items()}}
        return {'farmer':orders[0],'hands':orders[1:],'market':market}
