"""Rule-generated stochastic-disturbance state-graph Hierarchical MoE."""
import copy
__version__='v98-stochastic-disturbance-state-graph-moe-rc1';_MODE='ablation';_FULL=_MODE=='full';_MOVES={'NORTH':(0,-1),'SOUTH':(0,1),'EAST':(1,0),'WEST':(-1,0)};_CROPS=('WHEAT','CARROT','TOMATO','STRAWBERRY','MELON');_COST={'WHEAT':10,'CARROT':20,'TOMATO':50,'STRAWBERRY':100,'MELON':80};_MAT={'WHEAT':4,'CARROT':3,'TOMATO':8,'STRAWBERRY':10,'MELON':12};_SHOP={'BAKERY':{'WHEAT'},'BRUNCH_SPOT':{'WHEAT','STRAWBERRY'},'FARMERS_MARKET':{'WHEAT','CARROT','TOMATO','STRAWBERRY'},'ICE_CREAM_SHOP':{'WHEAT','STRAWBERRY'},'PET_CAFE':{'CARROT'},'PIZZA_SHOP':{'WHEAT','TOMATO'},'SMOOTHIE_SHOP':{'STRAWBERRY'},'YARN_STORE':set()};_STATE={0:{},1:{}}
def _get(v,k,d=None):
 if isinstance(v,dict):return v.get(k,d)
 g=getattr(v,'get',None);return g(k,d) if callable(g) else getattr(v,k,d)
def _seat(o):return 1 if int(_get(o,'player',0) or 0)==1 else 0
def _step(o):
 x=_get(o,'step',None);return min(718,max(0,int(x if x is not None else int(_get(o,'day',0) or 0)*24+int(_get(o,'hour',0) or 0))))
def _farm(o):
 fs=list(_get(o,'farms',[]) or []);s=_seat(o);return fs[s] if s<len(fs) else {}
def _positions(o):
 f=_farm(o);return [tuple(map(int,_get(f,'farmer',[4,4]))),*[tuple(map(int,p)) for p in list(_get(f,'hands',[]) or [])]]
def _record(st,e,n=1):st['experts'][e]=int(st['experts'].get(e,0))+n
def _crop(o,x,y):
 day=int(_get(o,'day',0) or 0);remain=30-day
 if remain<4:return 'WHEAT','terminal_quick'
 if not _FULL:
  crop=('WHEAT','WHEAT','CARROT','STRAWBERRY','MELON')[(x*3+y*5)%5];return crop,'fixed_mix'
 demanded=set()
 for shop in list(_get(_get(o,'town',{}) or {},'unlocked_shops',[]) or []):demanded.update(_SHOP.get(str(shop),set()))
 if 'CARROT' in demanded and (x+y)%4==0:return 'CARROT','quick_root'
 if 'TOMATO' in demanded and remain>=8 and (x+y)%5==0:return 'TOMATO','demand_perennial'
 if 'STRAWBERRY' in demanded and remain>=10 and (x+y)%3==0:return 'STRAWBERRY','demand_perennial'
 if remain>=12 and (x*7+y)%5==0:return 'MELON','premium_melon'
 return 'WHEAT','feed_grain'
def _tasks(o,st):
 f=_farm(o);rows=list(_get(f,'tiles',[]) or []);tasks=[]
 for y,row in enumerate(rows):
  for x,t in enumerate(row):
   if t=='LOCKED':continue
   crop,expert=_crop(o,x,y)
   if isinstance(t,dict) and t.get('kind')=='WEED':tasks.append((0,x,y,['DIG'],'state_repair'))
   elif t is None:tasks.append((3,x,y,['PLANT',crop],expert))
   elif isinstance(t,dict) and t.get('kind')=='PLANT':
    if int(t.get('yield_units',0) or 0)>0:tasks.append((0,x,y,['HARVEST'],'harvest'))
    elif not t.get('watered_today'):tasks.append((1,x,y,['WATER'],'crop_maintenance'))
 return tasks
def _toward(p,t):
 if p[0]<t[0]:return ['EAST']
 if p[0]>t[0]:return ['WEST']
 if p[1]<t[1]:return ['SOUTH']
 if p[1]>t[1]:return ['NORTH']
 return ['PASS']
def _units(o,st):
 positions=_positions(o);tasks=_tasks(o,st);seeds={k:max(0,int(v or 0)) for k,v in dict(_get(_get(o,'private',{}) or {},'seeds',{}) or {}).items()};pairs=[]
 for i,p in enumerate(positions):
  for j,t in enumerate(tasks):pairs.append((t[0],abs(p[0]-t[1])+abs(p[1]-t[2]),i,j))
 pairs.sort();used_i=set();used_j=set();assign={}
 for _,_,i,j in pairs:
  if i not in used_i and j not in used_j:used_i.add(i);used_j.add(j);assign[i]=j
 out=[]
 for i,p in enumerate(positions):
  if i not in assign:out.append(['PASS']);_record(st,'safe_idle');continue
  t=tasks[assign[i]];a=list(t[3]) if p==(t[1],t[2]) else _toward(p,(t[1],t[2]));expert=t[4] if p==(t[1],t[2]) else 'logistics_execution'
  if a[0]=='PLANT':
   if seeds.get(a[1],0)<=0:a=['PASS'];expert='safe_idle'
   else:seeds[a[1]]-=1
  out.append(a);_record(st,expert)
 return out
def _market(o,st):
 f=_farm(o);private=_get(o,'private',{}) or {};shed={k:max(0,int(v or 0)) for k,v in dict(_get(private,'shed',{}) or {}).items()};seeds={k:max(0,int(v or 0)) for k,v in dict(_get(private,'seeds',{}) or {}).items()};orders=[]
 for item,q in shed.items():
  if item in _CROPS or item in {'EGG','MILK','WOOL','FERTILIZER'}:
   if q>0:orders.append(['SELL',item,q]);_record(st,'product_liquidation')
 desired=12;hands=len(list(_get(f,'hands',[]) or []))
 for _ in range(max(0,min(desired-hands,10-len(orders)))):orders.append(['HIRE']);_record(st,'labor_expansion')
 money=max(0,int(_get(f,'money',0) or 0));quads=len(list(_get(f,'unlocked_quadrants',[]) or []));land_cost=(1000,2000,4000)
 if quads<4 and len(orders)<10 and money>=land_cost[quads-1]+300:orders.append(['BUY_LAND']);_record(st,'land_expansion')
 needs={c:0 for c in _CROPS}
 for _,x,y,a,_ in _tasks(o,st):
  if a[0]=='PLANT':needs[a[1]]+=1
 for c in _CROPS:
  q=max(0,min(needs[c]-seeds.get(c,0),20))
  if q and len(orders)<10:orders.append(['BUY_SEED',c,q]);_record(st,'seed_procurement')
 return orders[:10]
def _reset(o):
 s,step=_seat(o),_step(o);st=_STATE[s]
 if step==0 or step<int(st.get('last',-1)):st.clear();st.update(last=step,calls=0,experts={},fallback=0,changed_calls=0)
 st['last']=step;st['calls']=int(st.get('calls',0))+1;return st
def _fallback(o):return {'farmer':['PASS'],'hands':[['PASS'] for _ in list(_get(_farm(o),'hands',[]) or [])],'market':[]}
def model_status():return {'kind':'v98_stochastic_disturbance_state_graph_moe','model_id':'v98_stochastic_disturbance_state_graph_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','mode':_MODE,'router':'reachable-tile-task-graph','experts':['feed_grain','quick_root','demand_perennial','premium_melon','terminal_quick','state_repair','crop_maintenance','harvest','logistics_execution','product_liquidation','labor_expansion','land_expansion','seed_procurement'],'stats':copy.deepcopy(_STATE)}
def agent(obs,configuration=None):
 del configuration
 try:
  st=_reset(obs);orders=_units(obs,st);market=_market(obs,st);return {'farmer':orders[0],'hands':orders[1:],'market':market}
 except Exception:_STATE[_seat(obs)]['fallback']=int(_STATE[_seat(obs)].get('fallback',0))+1;return _fallback(obs)
