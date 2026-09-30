"""dda: complete joint-action support, selected from current visible state.

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
        self.last={};self.credits={};self.stats['preempted_units']=0
        self.bw=np.asarray([8]*13+[6,2,1,2,1,1,30,10],np.float32)
        self.uw=np.asarray([30,0,100,100]+[400]*12,np.float32)

    def choose(self,obs):
        k=self.config['fixed_prototype']
        self.prev=k;self.last={'support_index':k,'mode':self.config['market_mode']}
        return k

    def improve_unit(self,obs,i,t,k,tok):
        if tok!=space.UNIT_INDEX['WATER'] or t//24>=28:return tok
        f=obs['farms'][obs['player']];pos=space.unit_position(obs,i);tile=f['tiles'][pos[1]][pos[0]];day=t//24
        if not isinstance(tile,dict) or tile.get('crop') not in ['TOMATO','STRAWBERRY']:return tok
        if tile.get('watered_today') or tile.get('consecutive_unwatered',0)>0 or tile.get('fertilized_until_day',-1)>=day:return tok
        if space.unit_inventory(obs,i).get('FERTILIZER',0)<=0:return tok
        if not hasattr(self,'water_days'):
            self.water_days=np.zeros((30,10,10),bool)
            tokens=self.arr['unit_tokens'][:,k];units=self.arr['units'][:,k]
            for tt,ii in np.argwhere(tokens==space.UNIT_INDEX['WATER']):
                xy=np.rint(units[tt,ii,2:4].astype(float)*9).astype(int)
                self.water_days[tt//24,xy[1],xy[0]]=True
            self.stats['water_to_fertilize']=0
        if not self.water_days[day+1,pos[1],pos[0]]:return tok
        cd=rules.CROPS[tile['crop']];bonus=0
        for d in [day+2,day+3]:
            age=d-tile['planted_day']-cd['first_yield_day']
            if d<30 and age>=0 and age%cd['interval']==0 and age//cd['interval']+1<=cd['max_yield'] and self.water_days[d-1,pos[1],pos[0]]:bonus+=1
        if bonus*obs['market']['prices'][tile['crop']]<=obs['market']['prices']['FERTILIZER']*1.1:return tok
        self.stats['water_to_fertilize']+=1
        return space.UNIT_INDEX['FERTILIZE']

    def act(self,obs):
        t=int(obs['step'])
        if t==0:self.prev=-1;self.credits={}
        k=self.choose(obs);shadow=copy.deepcopy(obs);s=space.seat(obs)
        orders=[]
        for i in range(space.unit_count(obs)):
            tok=int(self.arr['unit_tokens'][t,k,i]) if i<16 else 0
            qty=int(self.arr['unit_quantities'][t,k,i]) if i<16 else 0
            tok=self.improve_unit(shadow,i,t,k,tok)
            if not space.unit_legal_mask(shadow,i)[tok]:
                self.stats['invalid_units']+=1;tok=0
            order=space.decode_unit(shadow,i,tok,qty);orders.append(order)
            rules._apply_unit_action(shadow['farms'][s],shadow['private'],i,order,10,t//24,24,100)
        market=[];sh=space.market_shadow(shadow)
        ms=copy.deepcopy(obs['market']);ms['params']=rules._resolve_market_params(ms.get('params'))
        for slot,(tok,qty) in enumerate(zip(self.arr['market_tokens'][t,k],self.arr['market_quantities'][t,k])):
            tok=int(tok);qty=int(qty)
            credit=self.credits.pop((t,slot),0)
            if credit and qty!=101:
                qty=max(0,qty-credit)
                if qty==0:continue
            if tok==0:break
            name=space.MARKET_TOKENS[tok]
            if name in ['SELL:TOMATO','SELL:STRAWBERRY']:qty=101
            if self.config['market_mode']=='sellall' and name.startswith('SELL:') and name!='SELL:WHEAT':qty=101
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
        # With no town consumption this step, non-buyable goods cannot obtain a
        # better next-step quote through exogenous inventory withdrawals.
        if t<718 and t%4!=0:
            for slot,(tok,qty) in enumerate(zip(self.arr['market_tokens'][t+1,k],self.arr['market_quantities'][t+1,k])):
                name=space.MARKET_TOKENS[int(tok)]
                if name=='STOP' or len(market)>=10:break
                if not name.startswith('SELL:'):continue
                item=name.split(':')[1]
                if item in ['WHEAT','FERTILIZER']:continue
                available=shadow['private']['shed'].get(item,0)
                q=available if int(qty)==101 else min(available,int(qty))
                done=0
                for _ in range(q):
                    price=rules.market_price(item,ms['inventory'][item],ms['params'])
                    if not rules._commit_unit('SELL',item,price,shadow['farms'][s],shadow['private'],ms,100):break
                    done+=1
                if done:
                    market.append(['SELL',item,done]);self.credits[t+1,slot]=done
                    self.stats['preempted_units']+=done
        self.stats['calls']+=1
        return {'farmer':orders[0],'hands':orders[1:],'market':market}

_AGENT=None
def agent(obs,configuration=None):
    global _AGENT
    if _AGENT is None:_AGENT=Agent()
    return _AGENT.act(obs)
