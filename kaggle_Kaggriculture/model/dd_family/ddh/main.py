"""ddh: release-time constrained teacher task queues support, selected from current visible state.

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

    def make_plan(self,obs):
        t=obs['step'];self.day=t//24;self.k=self.choose(obs);self.tasks=[];self.ptr=[0]*16
        for i in range(16):
            events=[]
            for tt in range(t,min(719,(self.day+1)*24)):
                tok=int(self.arr['unit_tokens'][tt,self.k,i]);name=space.UNIT_TOKENS[tok]
                if name in ['PASS','NORTH','SOUTH','EAST','WEST']:continue
                pos=np.rint(self.arr['units'][tt,self.k,i,2:4].astype(float)*9).astype(int).tolist()
                events.append((tt,pos,tok,int(self.arr['unit_quantities'][tt,self.k,i])))
            self.tasks.append(events)
        self.stats.setdefault('plans',0);self.stats['plans']+=1

    def done(self,obs,i,event):
        tt,pos,tok,qty=event;name=space.UNIT_TOKENS[tok];x,y=pos
        tile=obs['farms'][obs['player']]['tiles'][y][x]
        inv=space.unit_inventory(obs,i)
        if name=='WATER':return not isinstance(tile,dict) or not tile.get('crop') or tile.get('watered_today')
        if name=='FEED':return not isinstance(tile,dict) or not tile.get('animal') or tile.get('fed_today')
        if name=='CARE':return not isinstance(tile,dict) or not tile.get('animal') or tile.get('cared_today')
        if name=='HARVEST':return not isinstance(tile,dict) or not tile.get('yield_units',0)
        if name=='COLLECT_FERTILIZER':return not isinstance(tile,dict) or not tile.get('fertilizer_available')
        if name=='FERTILIZE':return not isinstance(tile,dict) or not tile.get('crop') or tile.get('fertilized_until_day',-1)>=self.day
        if name.startswith('PLANT:'):return isinstance(tile,dict) and bool(tile.get('crop') or tile.get('animal'))
        if name.startswith('BUILD_'):return isinstance(tile,dict) and tile.get('kind')==name[6:]
        if name=='DROP':return not sum(inv.values())
        if name.startswith('PLACE:'):
            item=name.split(':')[1]
            return not inv.get(item,0) or (item in space.ANIMALS and isinstance(tile,dict) and bool(tile.get('animal')))
        if name.startswith('PICKUP:'):
            item=name.split(':')[1]
            return qty!=101 and inv.get(item,0)>=qty
        if name=='DIG':return tile is None
        return False

    def next_event(self,obs,i):
        while self.ptr[i]<len(self.tasks[i]):
            event=self.tasks[i][self.ptr[i]]
            if obs['step']>=event[0] and self.done(obs,i,event):self.ptr[i]+=1
            else:return event
        return None

    def task_action(self,obs,i):
        event=self.next_event(obs,i)
        if event is None:return ['PASS']
        tt,target,tok,qty=event;pos=space.unit_position(obs,i);name=space.UNIT_TOKENS[tok]
        # Wait only when a task depends on an hourly refresh; use freed movement slack otherwise.
        if pos!=tuple(target):
            if pos[0]<target[0]:return ['EAST']
            if pos[0]>target[0]:return ['WEST']
            if pos[1]<target[1]:return ['SOUTH']
            return ['NORTH']
        if obs['step']<tt:return ['PASS']
        order=space.decode_unit(obs,i,tok,qty)
        if order[0]=='PASS':return order
        self.ptr[i]+=1
        return order

    def market_tasks(self,obs):
        t=obs['step'];seat=obs['player'];farm=obs['farms'][seat];private=obs['private'];market=obs['market'];orders=[]
        market['params']=rules._resolve_market_params(market.get('params'))
        def emit(op,item=None,q=1):
            if len(orders)>=10:return
            if op=='HIRE':
                if len(farm['hands'])>=15 or farm['money']<space._fib(farm['hires_today']):return
                cost=space._fib(farm['hires_today']);farm['money']-=cost;farm['hires_today']+=1;farm['hands'].append([4,4]);private['inventories'].append({});orders.append(['HIRE']);return
            if op=='BUY_LAND':
                k=len(farm['unlocked_quadrants'])-1
                if k<3 and farm['money']>=rules.LAND_PRICES[k]:farm['money']-=rules.LAND_PRICES[k];farm['unlocked_quadrants'].append(rules.LAND_ORDER[k]);orders.append(['BUY_LAND'])
                return
            done=0
            for _ in range(max(0,int(q))):
                price=(rules.CROPS[item]['seed'] if op=='BUY_SEED' else rules.ANIMALS[item]['cost'] if op=='BUY_ANIMAL' else rules.market_price(item,market['inventory'][item],market['params']))
                if not rules._commit_unit(op,item,price,farm,private,market,100):break
                done+=1
            if done:orders.append([op,item,done])
        # Sales are based on actual production. Teacher tasks determine resource demands.
        for item in space.PRODUCTS:
            if item!='WHEAT' and private['shed'].get(item,0):emit('SELL',item,private['shed'][item])
        # Retain learned investment and hire timing; quantities react to actual inventories below.
        for tok,qty in zip(self.arr['market_tokens'][t,self.k],self.arr['market_quantities'][t,self.k]):
            name=space.MARKET_TOKENS[int(tok)]
            if name=='STOP':break
            if name in ['HIRE','BUY_LAND']:emit(name)
            elif name.startswith(('BUY_SEED:','BUY_ANIMAL:')):
                op,item=name.split(':');emit(op,item,int(qty) if qty!=101 else 1)
        # Resource requirements for each unit's immediate pending task.
        needs={};seedneeds={}
        for i in range(min(16,1+len(farm['hands']))):
            e=self.next_event(obs,i)
            if e is None:continue
            name=space.UNIT_TOKENS[e[2]]
            if name.startswith('PICKUP:'):
                item=name.split(':')[1];q=e[3] if e[3]!=101 else 1
                needs[item]=needs.get(item,0)+max(0,q-space.unit_inventory(obs,i).get(item,0))
            elif name.startswith('PLANT:'):
                item=name.split(':')[1];seedneeds[item]=seedneeds.get(item,0)+1
        for item,n in needs.items():
            shortage=max(0,n-private['shed'].get(item,0))
            if shortage:emit('BUY_ANIMAL' if item in space.ANIMALS else 'BUY_PRODUCT',item,shortage)
        for item,n in seedneeds.items():
            shortage=max(0,n-private['seeds'].get(item,0))
            if shortage:emit('BUY_SEED',item,shortage)
        if t>=696:
            n=private['shed'].get('WHEAT',0)
            if n:emit('SELL','WHEAT',n)
        return orders

    def act(self,obs):
        if obs['step']==0:self.prev=-1;self.day=-1
        if self.day!=obs['step']//24:self.make_plan(obs)
        shadow=copy.deepcopy(obs);s=obs['player'];orders=[]
        for i in range(space.unit_count(obs)):
            order=self.task_action(shadow,i) if i<16 else ['PASS'];orders.append(order)
            rules._apply_unit_action(shadow['farms'][s],shadow['private'],i,order,10,self.day,24,100)
        market=self.market_tasks(shadow);self.stats['calls']+=1
        self.last={'support_index':self.k,'task_pointers':list(self.ptr)}
        return {'farmer':orders[0],'hands':orders[1:],'market':market}

_AGENT=None
def agent(obs,configuration=None):
    global _AGENT
    if _AGENT is None:_AGENT=Agent()
    return _AGENT.act(obs)
