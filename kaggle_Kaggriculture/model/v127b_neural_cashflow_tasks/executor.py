"""Feedback task execution. Economic targets come only from the daily plan.

Mandatory feed/water are lifecycle dependencies of held assets, not learned raw
moves. Uses current observations, persistent task claims, and deterministic rule
projection. No teacher replay or parent agent is called.
"""
import copy,collections
import action_space as A
import rules
import budget
from plan_features import TYPES,CROPS,ANIMALS
SHED=((4,4),(5,4),(4,5),(5,5))
def dist(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def nearest(p):return min(SHED,key=lambda q:(dist(p,q),q))
def move(p,q):
 if p[0]<q[0]:return ['EAST']
 if p[0]>q[0]:return ['WEST']
 if p[1]<q[1]:return ['SOUTH']
 if p[1]>q[1]:return ['NORTH']
 return ['PASS']
def cells(f):
 for y,row in enumerate(f['tiles']):
  for x,t in enumerate(row):yield x,y,t
def expandable(t):return t is None or (isinstance(t,dict) and not t.get('animal') and not t.get('crop'))
def target_at(plan,x,y):return TYPES[int(plan['tiles'][y*10+x])]
def deficits(obs,plan):
 desired=collections.Counter(TYPES[int(v)] for v in plan['tiles'])
 actual=collections.Counter((t.get('animal') or t.get('crop')) for _,_,t in cells(obs['farms'][obs['player']]) if isinstance(t,dict))
 return {name:max(0,desired[name]-actual[name]) for name in CROPS+ANIMALS}
def needs(obs,plan):
 counts=collections.Counter();f=obs['farms'][obs['player']];day=obs['step']//24
 for x,y,t in cells(f):
  name=target_at(plan,x,y)
  if not expandable(t):continue
  if name in CROPS and day+rules.CROPS[name]['first_yield_day']<30:counts[name]+=1
  elif name in ANIMALS and day+rules.ANIMALS[name]['first_yield_day']<30:counts[name]+=1
 return collections.Counter({name:min(n,deficits(obs,plan)[name]) for name,n in counts.items()})

class Executor:
 def __init__(self,mode='full'):
  self.goals={};self.day=-1;self.plan=None;self.stats=collections.Counter();self.mode=mode;self.feedback_log=[];self.feedback={};self.expected=None;self.blocked=collections.Counter()
 def set_plan(self,plan,day):self.plan=plan;self.day=day;self.goals={};self.stats['plans']+=1
 def jobs(self,obs):
  f=obs['farms'][obs['player']];day=obs['step']//24;hour=obs['step']%24;j=[];remaining=deficits(obs,self.plan)
  for x,y,t in cells(f):
   if isinstance(t,dict) and t.get('animal'):
    if day<29 and not t['fed_today']:j.append(('FEED',x,y,'WHEAT',110+25*t.get('consecutive_unfed',0)))
    if t.get('yield_units',0)>0:j.append(('HARVEST',x,y,'',82))
    if t.get('fertilizer_available'):j.append(('COLLECT_FERTILIZER',x,y,'',76))
    if day<29 and not t.get('cared_today'):j.append(('CARE',x,y,'',54))
   elif isinstance(t,dict) and t.get('crop'):
    crop=t['crop'];cd=rules.CROPS[crop];age=day-t['planted_day'];ready=t.get('yield_units',0)>0 and age>=cd['first_yield_day'] and (cd['ongoing'] or age>=cd['max_yield_day'] or t['yield_units']>=cd['max_yield'] or day==29)
    if ready:j.append(('HARVEST',x,y,'',90 if not cd['ongoing'] else 82))
    if not t['watered_today'] and not (ready and not cd['ongoing']) and (day<29 or (not cd['ongoing'] and t.get('yield_units',0)<cd['max_yield'])):j.append(('WATER',x,y,'',100+20*t.get('consecutive_unwatered',0)))
   if expandable(t):
    goal=target_at(self.plan,x,y)
    if goal in ANIMALS and remaining[goal]>0 and day+rules.ANIMALS[goal]['first_yield_day']<30:j.append(('ANIMAL',x,y,goal,67))
    if goal in CROPS and remaining[goal]>0 and day+rules.CROPS[goal]['first_yield_day']<30:j.append(('PLANT',x,y,goal,62))
  return j
 def action_for(self,obs,index,job):
  kind,x,y,item,_=job;p=A.unit_position(obs,index);inv=A.unit_inventory(obs,index);shed=obs['private']['shed'];t=obs['farms'][obs['player']]['tiles'][y][x]
  if kind in ['FEED','ANIMAL'] and inv.get(item,0)<=0:
   available=shed.get(item,0)
   if available<=0:return None
   if p not in SHED:return move(p,nearest(p))
   qty=min(3,available) if kind=='FEED' else 1
   return ['PICKUP',item,qty]
  if kind=='PLANT' and obs['private']['seeds'].get(item,0)<=0:return None
  if p!=(x,y):return move(p,(x,y))
  if kind=='ANIMAL':
   structure=rules.ANIMALS[item]['structure']
   if t is None:return ['BUILD_'+structure]
   if t.get('kind')!=structure:return ['DIG']
   return ['PLACE',item,1]
  if kind=='PLANT':return ['PLANT',item] if t is None else ['DIG']
  return [kind]
 def route_cost(self,obs,i,job):
  kind,x,y,item,_=job;p=A.unit_position(obs,i);inv=A.unit_inventory(obs,i)
  if kind in ['FEED','ANIMAL'] and inv.get(item,0)<=0:
   if obs['private']['shed'].get(item,0)<=0:return 999
   return min(dist(p,q)+1+dist(q,(x,y))+1 for q in SHED)+(1 if kind=='ANIMAL' else 0)
  if kind=='PLANT' and obs['private']['seeds'].get(item,0)<=0:return 999
  return dist(p,(x,y))+1+(1 if kind=='ANIMAL' else 0)
 def deposit_order(self,obs,i):
  inv=A.unit_inventory(obs,i);room=100-sum(obs['private']['shed'].values())
  if room<=0:return ['PASS']
  if sum(inv.values())<=room and not any(inv.get(k,0)>0 for k in ('WHEAT',)+ANIMALS):return ['DROP']
  products=[k for k in A.PRODUCTS if k!='WHEAT' and inv.get(k,0)>0]
  if not products:return ['PASS']
  item=max(products,key=lambda k:obs['market']['prices'].get(k,0)*min(room,inv[k]))
  return ['PLACE',item,min(room,inv[item])]
 def unit_actions(self,obs):
  shadow=copy.deepcopy(obs);seat=obs['player'];count=A.unit_count(obs);out=[];claimed=set();day=obs['step']//24;left=min(24-obs['step']%24,719-obs['step'])
  for i in range(count):
   pos=A.unit_position(shadow,i);inv=A.unit_inventory(shadow,i);cargo=sum(v for k,v in inv.items() if k in A.PRODUCTS and k!='WHEAT');home=nearest(pos)
   # Same-turn deposit becomes available to subsequent units and market.
   deposit=cargo>0 and (pos in SHED or cargo>=8 or (day==29 and left<=dist(pos,home)+1))
   if deposit:
    action=self.deposit_order(shadow,i) if pos in SHED else move(pos,home);self.stats['deposit_actions']+=1
   else:
    candidates=[]
    available_jobs=self.jobs(shadow);available_keys={job[:4] for job in available_jobs};claimed.intersection_update(available_keys)
    remaining=deficits(shadow,self.plan)
    for job in available_jobs:
     key=job[:4]
     if job[0] in ['PLANT','ANIMAL'] and sum(k[0]==job[0] and k[3]==job[3] for k in claimed)>=remaining[job[3]]:continue
     if key in claimed:continue
     cost=self.route_cost(shadow,i,job)
     if cost>left:continue
     if self.mode=='full' and job[0] in ['PLANT','ANIMAL']:
      extra=1 if job[0]=='PLANT' or inv.get('WHEAT',0)>0 else 2*dist((job[1],job[2]),nearest((job[1],job[2])))+2
      if cost+extra>left:self.blocked['GROWTH_DEADLINE']+=1;continue
     if day==29 and job[0] in ['HARVEST','COLLECT_FERTILIZER'] and cost+dist((job[1],job[2]),nearest((job[1],job[2])))+1>left:continue
     score=job[4]-3*cost+(10 if self.goals.get(i)==key else 0)
     candidates.append((score,job))
    if candidates:
     job=max(candidates,key=lambda z:(z[0],-z[1][2],-z[1][1]))[1];self.goals[i]=job[:4];claimed.add(job[:4]);action=self.action_for(shadow,i,job) or ['PASS']
    else:
     self.goals.pop(i,None)
     action=(self.deposit_order(shadow,i) if pos in SHED else move(pos,home)) if cargo else ['PASS']
   self.stats[action[0]]+=1;out.append(action)
   rules._apply_unit_action(shadow['farms'][seat],shadow['private'],i,action,10,day,24,100)
  return out,shadow
 def legacy_budget_market(self,obs):
  f=obs['farms'][obs['player']];private=obs['private'];market=obs['market'];market['params']=rules._resolve_market_params(market.get('params'));orders=[];day=obs['step']//24
  def emit(op,item=None,n=1,reserve=0):
   if len(orders)>=10:return 0
   if op=='HIRE':
    cost=A._fib(f['hires_today'])
    if f['money']-reserve<cost or len(f['hands'])>=15:return 0
    f['money']-=cost;f['hires_today']+=1;f['hands'].append([4,4]);orders.append(['HIRE']);return 1
   if op=='BUY_LAND':
    k=len(f['unlocked_quadrants'])-1
    reserve=max(reserve,budget.commitments(obs,self.plan)['cash_floor'])
    if k>=3 or f['money']-reserve<rules.LAND_PRICES[k]:return 0
    f['money']-=rules.LAND_PRICES[k];f['unlocked_quadrants'].append(rules.LAND_ORDER[k]);orders.append(['BUY_LAND']);return 1
   done=0
   for _ in range(max(0,int(n))):
    price=(rules.CROPS[item]['seed'] if op=='BUY_SEED' else rules.ANIMALS[item]['cost'] if op=='BUY_ANIMAL' else rules.market_price(item,market['inventory'][item],market['params']))
    floor=budget.commitments(obs,self.plan,1 if op=='BUY_ANIMAL' else 0)['cash_floor'] if op in ['BUY_ANIMAL','BUY_SEED'] else reserve
    if op!='SELL' and f['money']-max(reserve,floor)<price:break
    if not rules._commit_unit(op,item,price,f,private,market,100):break
    done+=1
   if done:orders.append([op,item,done])
   return done
  existing=sum(bool(t.get('animal')) for _,_,t in cells(f) if isinstance(t,dict));wanted=needs(obs,self.plan);food_target=max(3,existing+sum(wanted[a] for a in ANIMALS));food_target=0 if day==29 else food_target
  # Sell output to fund plan execution; food is reserved for maintenance.
  for item in sorted((p for p in A.PRODUCTS if p!='WHEAT'),key=lambda p:-private['shed'].get(p,0)*market['prices'].get(p,0)):
   if private['shed'].get(item,0):emit('SELL',item,private['shed'][item])
  carried=collections.Counter()
  for inv in private['inventories']:carried.update(inv)
  wheat=private['shed'].get('WHEAT',0)+carried['WHEAT']
  surplus=min(private['shed'].get('WHEAT',0),max(0,wheat-food_target))
  if surplus:emit('SELL','WHEAT',surplus)
  if wheat<food_target:emit('BUY_PRODUCT','WHEAT',food_target-wheat)
  target_hands=int(self.plan['hands'])
  for _ in range(max(0,target_hands-len(f['hands']))):
   if not emit('HIRE'):break
  reserve=max(0,existing-private['shed'].get('WHEAT',0)-carried['WHEAT'])*max(1,market['prices']['WHEAT'])
  if len(f['unlocked_quadrants'])<int(self.plan['land']):emit('BUY_LAND',reserve=reserve)
  for item in ANIMALS:
   required=max(0,wanted[item]-private['shed'].get(item,0)-carried[item])
   if required:emit('BUY_ANIMAL',item,required,reserve=reserve)
  for crop in CROPS:
   required=max(0,wanted[crop]-private['seeds'].get(crop,0))
   if required:emit('BUY_SEED',crop,required,reserve=reserve)
  return orders
 def market_actions(self,obs):
  if self.mode=='reserve_only':return self.legacy_budget_market(obs)
  f=obs['farms'][obs['player']];private=obs['private'];market=obs['market'];market['params']=rules._resolve_market_params(market.get('params'));orders=[];day=obs['step']//24
  def emit(op,item=None,n=1):
   if op not in ['HIRE','BUY_LAND'] and int(n)<=0:return 0
   if len(orders)>=10:self.blocked['ORDER_SLOTS']+=1;return 0
   if op=='HIRE':
    cost=A._fib(f['hires_today'])
    if f['money']<cost or len(f['hands'])>=15:self.blocked['HIRE_CASH']+=1;return 0
    f['money']-=cost;f['hires_today']+=1;f['hands'].append([4,4]);private['inventories'].append({});orders.append(['HIRE']);return 1
   if op=='BUY_LAND':
    k=len(f['unlocked_quadrants'])-1
    if k>=3:return 0
    if f['money']-budget.commitments(obs,self.plan)['cash_floor']<rules.LAND_PRICES[k]:self.blocked['LAND_CASH_RUNWAY']+=1;return 0
    f['money']-=rules.LAND_PRICES[k];f['unlocked_quadrants'].append(rules.LAND_ORDER[k]);orders.append(['BUY_LAND']);return 1
   done=0
   for _ in range(max(0,int(n))):
    price=(rules.CROPS[item]['seed'] if op=='BUY_SEED' else rules.ANIMALS[item]['cost'] if op=='BUY_ANIMAL' else rules.market_price(item,market['inventory'][item],market['params']))
    if op in ['BUY_ANIMAL','BUY_SEED']:
     floor=budget.commitments(obs,self.plan,1 if op=='BUY_ANIMAL' else 0)['cash_floor']
     if f['money']-price<floor:self.blocked['INVESTMENT_CASH_RUNWAY']+=1;break
     allowed,load=budget.labor_admission(obs,self.plan,item)
     if not allowed:self.blocked['INVESTMENT_LABOR']+=1;break
    if op!='SELL' and f['money']<price:self.blocked['MAINTENANCE_CASH']+=1;break
    if not rules._commit_unit(op,item,price,f,private,market,100):self.blocked['CAPACITY_OR_STOCK']+=1;break
    done+=1
   if done:orders.append([op,item,done])
   return done
  # Only realized warehouse production is credited as income.
  for item in sorted((p for p in A.PRODUCTS if p!='WHEAT'),key=lambda p:-private['shed'].get(p,0)*market['prices'].get(p,0)):
   if private['shed'].get(item,0):emit('SELL',item,private['shed'][item])
  commit=budget.commitments(obs,self.plan);next_food=commit['owned_animals'] if day<28 else 0
  food_target=commit['today_feed']+next_food
  surplus=min(private['shed'].get('WHEAT',0),max(0,commit['wheat_owned']-food_target))
  if surplus:emit('SELL','WHEAT',surplus)
  # Current feed first, then labor; unfunded future expansion cannot buy feed.
  if commit['wheat_owned']<commit['today_feed']:emit('BUY_PRODUCT','WHEAT',commit['today_feed']-commit['wheat_owned'])
  for _ in range(max(0,int(self.plan['hands'])-len(f['hands']))):
   if not emit('HIRE'):break
  wanted=needs(obs,self.plan);carried=collections.Counter()
  for inv in private['inventories']:carried.update(inv)
  # Fund the network's short-cycle crops before slow production expansion.
  for crop in CROPS:
   if rules.CROPS[crop]['first_yield_day']<=2:
    required=max(0,wanted[crop]-private['seeds'].get(crop,0));emit('BUY_SEED',crop,required)
  for item in ANIMALS:
   required=max(0,wanted[item]-private['shed'].get(item,0)-carried[item]);emit('BUY_ANIMAL',item,required)
  for crop in CROPS:
   if rules.CROPS[crop]['first_yield_day']>2:
    required=max(0,wanted[crop]-private['seeds'].get(crop,0));emit('BUY_SEED',crop,required)
  if len(f['unlocked_quadrants'])<int(self.plan['land']):emit('BUY_LAND')
  # Finance feed for animals just acquired, not the unreached neural wish-list.
  c=budget.commitments(obs,self.plan)
  food_target=c['today_feed']+(c['owned_animals'] if day<28 else 0)
  if c['wheat_owned']<food_target:emit('BUY_PRODUCT','WHEAT',food_target-c['wheat_owned'])
  return orders
 def observe_feedback(self,obs):
  f=obs['farms'][obs['player']];self.blocked=collections.Counter();shortfalls=[]
  if self.expected and self.expected['step']+1==obs['step'] and obs['step']%24!=0:
   if len(f['hands'])<self.expected['hands']:shortfalls.append('HIRE_NOT_FILLED')
   for category in ['shed','seeds']:
    for item,n in self.expected[category].items():
     if obs['private'][category].get(item,0)<n:shortfalls.append(category.upper()+'_SHORTFALL:'+item)
  c=budget.commitments(obs,self.plan)
  self.feedback={'step':obs['step'],'cash':f['money'],'actual_hands':len(f['hands']),'planned_hands':int(self.plan['hands']),'cash_runway':c,'market_shortfalls':shortfalls,'unmet_production':deficits(obs,self.plan)}
  if shortfalls:self.stats['market_shortfall_steps']+=1
  # Actual state, not assumed fill success, feeds all subsequent task compilation.
 def act(self,obs):
  self.observe_feedback(obs)
  units,shadow=self.unit_actions(obs);market=self.market_actions(shadow)
  f=shadow['farms'][obs['player']];self.expected={'step':obs['step'],'hands':len(f['hands']),'shed':dict(shadow['private']['shed']),'seeds':dict(shadow['private']['seeds'])}
  self.feedback['deferred_reasons']=dict(self.blocked);self.feedback['post_order_cash_runway']=budget.commitments(shadow,self.plan)
  self.feedback['post_order_projected_cash']=f['money']
  if obs['step']%24 in [0,22,23] or self.feedback['market_shortfalls']:self.feedback_log.append(copy.deepcopy(self.feedback))
  return {'farmer':units[0],'hands':units[1:],'market':market}
