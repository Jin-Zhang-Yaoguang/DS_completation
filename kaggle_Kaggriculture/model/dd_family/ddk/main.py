"""ddk: daily production-goal support, selected from current visible state.

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

    def plan(self,obs):
        t=obs['step'];self.day=t//24;self.k=self.choose(obs);end=min(718,self.day*24+23)
        b=self.arr['board'][end,self.k].reshape(100,21);self.goal=[]
        for row in b:
            animal=int(row[10:13].argmax());crop=int(row[5:10].argmax())
            self.goal.append(space.ANIMALS[animal] if row[10:13].max()>.5 else space.CROPS[crop] if row[5:10].max()>.5 else None)
        g=self.arr['global'][end,self.k];self.hands=int(round(float(g[7])*16));self.land=int(round(float(g[6])*4));self.claims={}
        self.stats.setdefault('plans',0);self.stats['plans']+=1

    @staticmethod
    def dist(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
    def home(self,p):return min(space.SHED_ACCESS,key=lambda q:(self.dist(p,q),q))
    def move(self,p,q):
        if p[0]<q[0]:return ['EAST']
        if p[0]>q[0]:return ['WEST']
        if p[1]<q[1]:return ['SOUTH']
        if p[1]>q[1]:return ['NORTH']
        return ['PASS']

    def requirements(self,obs):
        farm=obs['farms'][obs['player']];private=obs['private'];needs={p:0 for p in space.CROPS+space.ANIMALS}
        for y,row in enumerate(farm['tiles']):
            for x,tile in enumerate(row):
                if tile=='LOCKED':continue
                if isinstance(tile,dict) and (tile.get('crop') or tile.get('animal')):continue
                want=self.goal[y*10+x]
                if want in needs:
                    delay=rules.CROPS[want]['first_yield_day'] if want in space.CROPS else rules.ANIMALS[want]['first_yield_day']
                    if self.day+delay<29:needs[want]+=1
        return needs

    def bundles(self,obs):
        f=obs['farms'][obs['player']];jobs={}
        for y,row in enumerate(f['tiles']):
            for x,tile in enumerate(row):
                if tile=='LOCKED':continue
                pos=(x,y);want=self.goal[y*10+x];todo=[];priority=0
                if isinstance(tile,dict) and tile.get('animal'):
                    if self.day<29 and not tile['fed_today']:todo.append('FEED');priority=100+40*tile.get('consecutive_unfed',0)
                    if self.day<29 and not tile.get('cared_today'):todo.append('CARE');priority=max(priority,65)
                    if tile.get('yield_units',0)>0:todo.append('HARVEST');priority=max(priority,85)
                    if tile.get('fertilizer_available'):todo.append('COLLECT_FERTILIZER');priority=max(priority,70)
                elif isinstance(tile,dict) and tile.get('crop'):
                    crop=tile['crop'];cd=rules.CROPS[crop];age=self.day-tile['planted_day']
                    ready=tile.get('yield_units',0)>0 and age>=cd['first_yield_day'] and (cd['ongoing'] or age>=cd['max_yield_day'] or tile['yield_units']>=cd['max_yield'] or self.day==29)
                    if not tile['watered_today'] and (self.day<29 or not cd['ongoing']):
                        todo.append('WATER');priority=95+35*tile.get('consecutive_unwatered',0)
                    if ready:todo.append('HARVEST');priority=max(priority,90)
                elif want in space.CROPS and self.day+rules.CROPS[want]['first_yield_day']<29:
                    if tile is not None:todo.append('DIG')
                    todo.append('PLANT:'+want);priority=55
                elif want in space.ANIMALS and self.day+rules.ANIMALS[want]['first_yield_day']<29:
                    structure=rules.ANIMALS[want]['structure']
                    if tile is None:todo.append('BUILD_'+structure)
                    elif tile.get('kind')!=structure:todo+=['DIG','BUILD_'+structure]
                    todo.append('ANIMAL:'+want);priority=60
                if todo:jobs[pos]=(todo,priority)
        return jobs

    def action_for(self,obs,i,pos,todo):
        at=space.unit_position(obs,i);inv=space.unit_inventory(obs,i);shed=obs['private']['shed'];op=todo[0]
        # Fetch food for a short local tour; animal tasks acquire their cargo before departure.
        animal=next((o.split(':')[1] for o in todo if o.startswith('ANIMAL:')),None)
        if animal and inv.get(animal,0)<=0:
            if at not in space.SHED_ACCESS:return self.move(at,self.home(at))
            return ['PICKUP',animal,1] if shed.get(animal,0)>0 else None
        if (op=='FEED' or animal) and inv.get('WHEAT',0)<=0:
            if at not in space.SHED_ACCESS:return self.move(at,self.home(at))
            return ['PICKUP','WHEAT',min(3,shed.get('WHEAT',0))] if shed.get('WHEAT',0)>0 else None
        if op.startswith('PLANT:') and obs['private']['seeds'].get(op.split(':')[1],0)<=0:return None
        if at!=pos:return self.move(at,pos)
        if op.startswith('PLANT:'):return ['PLANT',op.split(':')[1]]
        if op.startswith('ANIMAL:'):return ['PLACE',op.split(':')[1],1]
        return [op]

    def unit_action(self,obs,i,jobs,claimed):
        pos=space.unit_position(obs,i);inv=space.unit_inventory(obs,i);home=self.home(pos);left=719-obs['step']
        cargo=sum(n for p,n in inv.items() if p in space.PRODUCTS and p!='WHEAT')
        total=sum(sum(v.values()) for v in obs['private']['inventories'])+sum(obs['private']['shed'].values())
        if cargo and (pos in space.SHED_ACCESS or (self.day==29 and left<=self.dist(pos,home)+2) or total>88 and cargo>=10):
            if pos!=home and pos not in space.SHED_ACCESS:return self.move(pos,home)
            items=[p for p in space.PRODUCTS if p!='WHEAT' and inv.get(p,0)>0]
            item=max(items,key=lambda p:inv[p]*obs['market']['prices'][p]);return ['PLACE',item,inv[item]]
        old=self.claims.get(i)
        if old in jobs and old not in claimed:
            action=self.action_for(obs,i,old,jobs[old][0])
            if action is not None:claimed.add(old);return action
        choices=[]
        remaining=min(24-obs['step']%24,719-obs['step'])
        for target,(todo,priority) in jobs.items():
            if target in claimed:continue
            cost=self.dist(pos,target)+len(todo)
            if (todo[0]=='FEED' or any(o.startswith('ANIMAL:') for o in todo)) and inv.get('WHEAT',0)<=0:
                cost=self.dist(pos,home)+1+self.dist(home,target)+len(todo)
            growth=any(o.startswith(('PLANT:','ANIMAL:')) for o in todo)
            if cost+(1 if growth else 0)>remaining:continue
            if self.day==29 and cost+self.dist(target,self.home(target))+1>remaining:continue
            action=self.action_for(obs,i,target,todo)
            if action is None:continue
            # Completing all local work saves repeated travel between global priority queues.
            score=priority-5*self.dist(pos,target)+4*len(todo)
            choices.append((score,target,action))
        if not choices:
            self.claims.pop(i,None)
            return ['PASS']
        _,target,action=max(choices,key=lambda z:(z[0],-z[1][1],-z[1][0]));self.claims[i]=target;claimed.add(target);return action

    def market(self,obs):
        f=obs['farms'][obs['player']];pr=obs['private'];m=obs['market'];m['params']=rules._resolve_market_params(m.get('params'));orders=[]
        def emit(op,item=None,n=1,reserve=0):
            if len(orders)>=10:return 0
            if op=='HIRE':
                cost=space._fib(f['hires_today'])
                if f['money']<cost:return 0
                f['money']-=cost;f['hires_today']+=1;f['hands'].append([4,4]);pr['inventories'].append({});orders.append(['HIRE']);return 1
            if op=='BUY_LAND':
                j=len(f['unlocked_quadrants'])-1
                if j>=3 or f['money']-reserve<rules.LAND_PRICES[j]:return 0
                f['money']-=rules.LAND_PRICES[j];f['unlocked_quadrants'].append(rules.LAND_ORDER[j]);orders.append(['BUY_LAND']);return 1
            done=0
            for _ in range(max(0,int(n))):
                price=rules.CROPS[item]['seed'] if op=='BUY_SEED' else rules.ANIMALS[item]['cost'] if op=='BUY_ANIMAL' else rules.market_price(item,m['inventory'][item]-(op=='BUY_PRODUCT'),m['params'])
                if op!='SELL' and f['money']-reserve<price:break
                if not rules._commit_unit(op,item,price,f,pr,m,100):break
                done+=1
            if done:orders.append([op,item,done])
            return done
        for item in space.PRODUCTS:
            if item!='WHEAT' and pr['shed'].get(item,0):emit('SELL',item,pr['shed'][item])
        carry={p:sum(inv.get(p,0) for inv in pr['inventories']) for p in space.ITEMS}
        animals=[t for row in f['tiles'] for t in row if isinstance(t,dict) and t.get('animal')]
        food=sum(not t['fed_today'] for t in animals) if self.day<29 else 0
        surplus=max(0,pr['shed'].get('WHEAT',0)+carry['WHEAT']-food)
        if surplus:emit('SELL','WHEAT',min(surplus,pr['shed'].get('WHEAT',0)))
        for _ in range(max(0,self.hands-len(f['hands']))):
            if not emit('HIRE'):break
        missing=max(0,food-pr['shed'].get('WHEAT',0)-carry['WHEAT'])
        if missing:emit('BUY_PRODUCT','WHEAT',missing)
        reserve=0
        if len(f['unlocked_quadrants'])<self.land:emit('BUY_LAND',reserve=reserve)
        needs=self.requirements(obs)
        for item in space.ANIMALS:
            n=max(0,needs[item]-pr['shed'].get(item,0)-carry[item])
            if n:
                got=emit('BUY_ANIMAL',item,n,reserve=50)
                if got:emit('BUY_PRODUCT','WHEAT',got)
        for item in sorted(space.CROPS,key=lambda p:rules.CROPS[p]['seed']):
            missing=max(0,needs[item]-pr['seeds'].get(item,0))
            if missing:emit('BUY_SEED',item,missing)
        return orders

    def act(self,obs):
        if obs['step']==0:self.prev=-1;self.day=-1
        if self.day!=obs['step']//24:self.plan(obs)
        shadow=copy.deepcopy(obs);seat=obs['player'];orders=[];claimed=set()
        for i in range(space.unit_count(obs)):
            order=self.unit_action(shadow,i,self.bundles(shadow),claimed);orders.append(order)
            rules._apply_unit_action(shadow['farms'][seat],shadow['private'],i,order,10,self.day,24,100)
        market=self.market(shadow);self.stats['calls']+=1
        self.last={'support_index':self.k,'target_hands':self.hands,'target_land':self.land}
        return {'farmer':orders[0],'hands':orders[1:],'market':market}

_AGENT=None
def agent(obs,configuration=None):
    global _AGENT
    if _AGENT is None:_AGENT=Agent()
    return _AGENT.act(obs)
