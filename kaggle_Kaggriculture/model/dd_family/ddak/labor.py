"""Dispatch only replay-completed workers; no y68 policy is used."""
import collections
import action_space as space,rules

class Dispatcher:
    def __init__(self,arr,k):
        self.ends={};self.last_hire={};self.planned={};self.day=-1;self.targets={}
        for d in range(30):
            lo=d*24;hi=min(lo+24,719);self.last_hire[d]=lo-1
            for i in range(16):
                active=[t for t in range(lo,hi) if int(arr['unit_tokens'][t,k,i])]
                self.ends[d,i]=max(active,default=lo-1)
            for t in range(lo,hi):
                if any(space.MARKET_TOKENS[int(tok)]=='HIRE' for tok in arr['market_tokens'][t,k]):self.last_hire[d]=t
                for i,tok in enumerate(arr['unit_tokens'][t,k]):
                    name=space.UNIT_TOKENS[int(tok)]
                    if name not in ['HARVEST','CARE','FEED']:continue
                    xy=tuple(round(float(n)*9) for n in arr['units'][t,k,i,2:4])
                    self.planned.setdefault((d,xy,name),[]).append(t)
        self.stats=collections.Counter()

    def remaining(self,d,xy,op,t):return any(tt>=t for tt in self.planned.get((d,xy,op),[]))

    def paths(self,farm,start):
        found={start:[]};queue=collections.deque([start])
        while queue:
            x,y=queue.popleft()
            for op,(dx,dy) in rules.FARMER_MOVES.items():
                pos=x+dx,y+dy;xx,yy=pos
                if 0<=xx<10 and 0<=yy<10 and farm['tiles'][yy][xx]!='LOCKED' and pos not in found:
                    found[pos]=found[x,y]+[op];queue.append(pos)
        return found

    def act(self,obs,i):
        t=int(obs['step']);day=t//24;end=min((day+1)*24,719);farm=space.own_farm(obs)
        if day!=self.day:self.day=day;self.targets={}
        if t<=self.ends.get((day,i),t) or t<=self.last_hire[day]:return None
        self.stats['eligible_steps']+=1
        start=space.unit_position(obs,i);paths=self.paths(farm,start);left=end-t
        claimed={target for ii,target in self.targets.items() if ii!=i};candidates=[]
        held=sum(obs['private']['shed'].values())+sum(sum(v.values()) for v in obs['private']['inventories'])
        for y,row in enumerate(farm['tiles']):
            for x,tile in enumerate(row):
                xy=x,y
                if xy not in paths or not isinstance(tile,dict) or not tile.get('animal'):continue
                distance=len(paths[xy]);spec=rules.ANIMALS[tile['animal']];price=obs['market']['prices'][spec['product']]
                for op in ['HARVEST','CARE']:
                    key=(xy,op)
                    if key in claimed or self.remaining(day,xy,op,t):continue
                    if op=='HARVEST':
                        if tile['yield_units']<=0 or held+tile['yield_units']>95:continue
                        value=tile['yield_units']*price
                    else:
                        if day>=28 or tile.get('cared_today'):continue
                        if not tile.get('fed_today') and not self.remaining(day,xy,'FEED',t):continue
                        first=tile['placed_day']+spec['first_yield_day']
                        production=max(day+1,first)
                        while (production-first)%spec['interval']:production+=1
                        if production>=30:continue
                        # Reward must still be collectible by a later planned visit.
                        if not any(dd>=production and self.planned.get((dd,xy,'HARVEST')) for dd in range(production,30)):continue
                        value=.7*price
                    deposit=min(abs(x-sx)+abs(y-sy) for sx,sy in space.SHED_ACCESS)+1 if day==29 else 0
                    if distance+1+deposit>left:continue
                    score=value/(distance+1)
                    if self.targets.get(i)==key:score*=1.05
                    candidates.append((score,value,-distance,xy,op))
        # On the final day no automatic shed deposit occurs.
        inventory=space.unit_inventory(obs,i)
        cash_held=sum(inventory.get(p,0)*obs['market']['prices'][p] for p in space.PRODUCTS if p not in ['WHEAT','FERTILIZER'])
        if day==29 and cash_held:
            sheds=[(len(paths[p]),p) for p in space.SHED_ACCESS if p in paths];dist,xy=min(sheds)
            if dist+1<=left and (left<=dist+2 or not candidates):candidates=[(float('inf'),cash_held,-dist,xy,'DROP')]
        if not candidates:self.targets.pop(i,None);return None
        _,value,_,xy,op=max(candidates);self.targets[i]=(xy,op)
        action=paths[xy][0] if paths[xy] else op
        self.stats[action]+=1
        if not paths[xy]:self.targets.pop(i,None)
        return space.UNIT_INDEX[action],0
