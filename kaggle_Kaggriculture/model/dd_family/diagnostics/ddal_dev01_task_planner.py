"""Distilled daily cell-task programs executed by interchangeable live workers."""
import collections,copy
import action_space as space,rules

TASKS={'FEED','CARE','HARVEST','COLLECT_FERTILIZER','WATER','FERTILIZE','DIG'}
class Planner:
 def __init__(self,arr,k):
  self.templates={};self.hires={};self.day=-1;self.jobs={};self.assigned={};self.stats=collections.Counter()
  for day in range(16,30):
   lo=day*24;hi=min(lo+24,719);jobs=collections.defaultdict(list)
   self.hires[day]=int(max(arr['units'][t,k,:,0].sum() for t in range(lo,hi)))-1
   for t in range(lo,hi):
    for i,tok in enumerate(arr['unit_tokens'][t,k]):
     name=space.UNIT_TOKENS[int(tok)]
     if name in TASKS or name.startswith('PLANT:'):
      xy=tuple(round(float(x)*9) for x in arr['units'][t,k,i,2:4]);jobs[xy].append(name)
   self.templates[day]=dict(jobs)

 def paths(self,farm,start):
  found={start:[]};queue=collections.deque([start])
  while queue:
   x,y=queue.popleft()
   for op,(dx,dy) in rules.FARMER_MOVES.items():
    pos=x+dx,y+dy;xx,yy=pos
    if 0<=xx<10 and 0<=yy<10 and farm['tiles'][yy][xx]!='LOCKED' and pos not in found:
     found[pos]=found[x,y]+[op];queue.append(pos)
  return found

 def clean(self,obs,xy):
  q=self.jobs[xy];x,y=xy;tile=space.own_farm(obs)['tiles'][y][x];day=int(obs['step'])//24
  while q:
   op=q[0];plant=isinstance(tile,dict) and tile.get('crop');animal=isinstance(tile,dict) and tile.get('animal');skip=False
   if op=='FEED':skip=not animal or tile.get('fed_today')
   elif op=='CARE':skip=not animal or tile.get('cared_today')
   elif op=='COLLECT_FERTILIZER':skip=not animal or not tile.get('fertilizer_available')
   elif op=='WATER':skip=not plant or tile.get('watered_today')
   elif op=='FERTILIZE':skip=not plant
   elif op=='HARVEST':skip=not (plant or animal) or tile.get('yield_units',0)<=0 or bool(plant and day-tile['planted_day']<space.CROP_FIRST_YIELD_DAY[plant])
   elif op=='DIG':skip=tile is None or bool(animal)
   elif op.startswith('PLANT:'):
    if animal or tile=='LOCKED':skip=True
    elif tile is not None:
     if plant and tile.get('yield_units',0)>0 and day-tile['planted_day']>=space.CROP_FIRST_YIELD_DAY[plant]:q.insert(0,'HARVEST')
     else:q.insert(0,'DIG')
     break
   if not skip:break
   q.pop(0);self.stats['obsolete_tasks']+=1
  return q

 def remaining(self,op):return sum(q.count(op) for q in self.jobs.values())

 def act(self,obs):
  t=int(obs['step']);day=t//24;end=min((day+1)*24,719);seat=space.seat(obs)
  if day!=self.day:
   if self.day>=0:self.stats['unfinished_tasks']+=sum(map(len,self.jobs.values()))
   self.day=day;self.jobs=copy.deepcopy(self.templates[day]);self.assigned={};self.stats['task_count']+=sum(map(len,self.jobs.values()))
  shadow=copy.deepcopy(obs);orders=[]
  for i in range(space.unit_count(obs)):
   farm=space.own_farm(shadow);start=space.unit_position(shadow,i);paths=self.paths(farm,start);inv=space.unit_inventory(shadow,i)
   for xy in self.jobs:self.clean(shadow,xy)
   if i in self.assigned and not self.jobs[self.assigned[i]]:self.assigned.pop(i)
   claimed={xy for ii,xy in self.assigned.items() if ii!=i};options=[]
   for xy,q in self.jobs.items():
    if not q or xy not in paths or xy in claimed:continue
    if i in self.assigned and xy!=self.assigned[i]:continue
    op=q[0];x,y=xy;tile=farm['tiles'][y][x];resource='WHEAT' if op=='FEED' else 'FERTILIZER' if op=='FERTILIZE' else None
    route=paths[xy];action=route[0] if route else op;qty=0;distance=len(route)
    if resource and not inv.get(resource):
     if not shadow['private']['shed'].get(resource):continue
     sheds=sorted((len(paths[p])+abs(p[0]-x)+abs(p[1]-y),len(paths[p]),p) for p in space.SHED_ACCESS if p in paths)
     if not sheds:continue
     cost,dist,shed=sheds[0];distance=cost+1
     if paths[shed]:action=paths[shed][0]
     else:action='PICKUP:'+resource;qty=min(3,shadow['private']['shed'][resource],max(1,self.remaining('FEED' if resource=='WHEAT' else 'FERTILIZE')))
    if op.startswith('PLANT:') and not shadow['private']['seeds'].get(op.split(':')[1],0):continue
    if distance+1>end-t:continue
    value=30.
    if isinstance(tile,dict):
     if op=='HARVEST':
      product=tile.get('crop') or rules.ANIMALS[tile['animal']]['product'];value=max(30,tile.get('yield_units',0)*obs['market']['prices'][product])
     elif op in ['FEED','CARE'] and tile.get('animal'):
      value=obs['market']['prices'][rules.ANIMALS[tile['animal']]['product']]
      if op=='FEED' and tile.get('consecutive_unfed',0):value*=3
     elif op=='WATER':value=150 if tile.get('consecutive_unwatered',0) else 60
     elif op=='FERTILIZE':value=60
    if op.startswith('PLANT:'):value=120
    # Finish short bundles, and raise priority as the daily deadline approaches.
    score=value/(distance+1)+20/(len(q)+1)
    options.append((score,xy,action,qty))
   if options:
    score,xy,action,qty=max(options);self.assigned[i]=xy
   else:
    self.assigned.pop(i,None);xy=None;action='PASS';qty=0
   # The final day has no automatic inventory settlement.
   if day==29 and sum(inv.get(p,0) for p in space.PRODUCTS if p not in ['WHEAT','FERTILIZER']):
    dist,shed=min((len(paths[p]),p) for p in space.SHED_ACCESS if p in paths)
    if end-t<=dist+2 or not options:
     action=paths[shed][0] if paths[shed] else 'DROP';qty=0;xy=None;self.assigned.pop(i,None)
   tok=space.UNIT_INDEX[action]
   if not space.unit_legal_mask(shadow,i)[tok]:action='PASS';tok=0;self.stats['invalid_requests']+=1
   order=space.decode_unit(shadow,i,tok,qty);orders.append(order)
   if xy is not None and not action.startswith('PICKUP:') and action not in space.MOVES and action!='PASS':
    assert self.jobs[xy][0]==action
    self.jobs[xy].pop(0);self.stats['completed_tasks']+=1
   self.stats[action]+=1
   rules._apply_unit_action(shadow['farms'][seat],shadow['private'],i,order,10,day,24,100)
  market=[];ms=copy.deepcopy(obs['market']);ms['params']=rules._resolve_market_params(ms.get('params'));farm=shadow['farms'][seat];priv=shadow['private']
  # Actual non-input stock is always realizable; no forecast sale is credited.
  for item in space.PRODUCTS:
   if item in ['WHEAT','FERTILIZER'] or len(market)>=10:continue
   done=0
   for _ in range(priv['shed'].get(item,0)):
    price=rules.market_price(item,ms['inventory'][item],ms['params'])
    if not rules._commit_unit('SELL',item,price,farm,priv,ms,100):break
    done+=1
   if done:market.append(['SELL',item,done])
  # Buy only this day's remaining seed commitments.
  for crop in space.CROPS:
   if len(market)>=10:break
   need=max(0,self.remaining('PLANT:'+crop)-priv['seeds'].get(crop,0));done=0
   for _ in range(need):
    if not rules._commit_unit('BUY_SEED',crop,space.SEED_COST[crop],farm,priv,ms,100):break
    done+=1
   if done:market.append(['BUY_SEED',crop,done])
  for item,op in [('WHEAT','FEED'),('FERTILIZER','FERTILIZE')]:
   if len(market)>=10:break
   held=priv['shed'].get(item,0)+sum(v.get(item,0) for v in priv['inventories'])
   need=max(0,self.remaining(op)-held);done=0
   for _ in range(need):
    price=rules.market_price(item,ms['inventory'][item]-1,ms['params'])
    if not rules._commit_unit('BUY_PRODUCT',item,price,farm,priv,ms,100):break
    done+=1
   if done:market.append(['BUY_PRODUCT',item,done])
  hires=farm['hires_today']
  while t%24<5 and hires<self.hires[day] and len(market)<10:
   cost=rules._fib(hires)
   if farm['money']<cost+100:break
   farm['money']-=cost;hires+=1;market.append(['HIRE']);self.stats['hires']+=1
  self.stats['calls']+=1
  if t==718:self.stats['unfinished_tasks']+=sum(map(len,self.jobs.values()))
  return {'farmer':orders[0],'hands':orders[1:],'market':market}
