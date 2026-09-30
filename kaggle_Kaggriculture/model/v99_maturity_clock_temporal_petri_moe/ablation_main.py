"""Rule-generated maturity-clock Temporal Petri Hierarchical MoE."""
import copy
__version__='v99-maturity-clock-temporal-petri-moe-rc1';_FULL='ablation'=='full';_CROPS=('WHEAT','CARROT','TOMATO','STRAWBERRY','MELON');_FIRST={'WHEAT':2,'CARROT':2,'TOMATO':8,'STRAWBERRY':10,'MELON':10};_MAX={'WHEAT':4,'CARROT':3,'TOMATO':8,'STRAWBERRY':10,'MELON':12};_SHOP={'BAKERY':{'WHEAT'},'BRUNCH_SPOT':{'WHEAT','STRAWBERRY'},'FARMERS_MARKET':{'WHEAT','CARROT','TOMATO','STRAWBERRY'},'ICE_CREAM_SHOP':{'WHEAT','STRAWBERRY'},'PET_CAFE':{'CARROT'},'PIZZA_SHOP':{'WHEAT','TOMATO'},'SMOOTHIE_SHOP':{'STRAWBERRY'},'YARN_STORE':set()};_STATE={0:{},1:{}}
def _g(v,k,d=None):
 if isinstance(v,dict):return v.get(k,d)
 f=getattr(v,'get',None);return f(k,d) if callable(f) else getattr(v,k,d)
def _seat(o):return int(_g(o,'player',0) or 0)
def _step(o):return min(718,max(0,int(_g(o,'step',0) or 0)))
def _farm(o):return list(_g(o,'farms',[]) or [])[_seat(o)]
def _pos(o):
 f=_farm(o);return [tuple(map(int,_g(f,'farmer',[4,4]))),*[tuple(map(int,p)) for p in list(_g(f,'hands',[]) or [])]]
def _rec(st,e):st['experts'][e]=int(st['experts'].get(e,0))+1
def _choice(o,x,y):
 day=int(_g(o,'day',0) or 0);remain=30-day;d=set()
 for s in list(_g(_g(o,'town',{}) or {},'unlocked_shops',[]) or []):d.update(_SHOP.get(str(s),set()))
 if remain<4:return 'WHEAT','terminal_quick'
 if 'CARROT' in d and (x+y)%4==0:return 'CARROT','quick_root'
 if 'TOMATO' in d and remain>=8 and (x+y)%5==0:return 'TOMATO','demand_perennial'
 if 'STRAWBERRY' in d and remain>=10 and (x+y)%3==0:return 'STRAWBERRY','demand_perennial'
 if remain>=12 and (x*7+y)%6==0:return 'MELON','premium_melon'
 return 'WHEAT','feed_grain'
def _tasks(o):
 day=int(_g(o,'day',0) or 0);rows=list(_g(_farm(o),'tiles',[]) or []);out=[]
 for y,row in enumerate(rows):
  for x,t in enumerate(row):
   if t=='LOCKED':continue
   crop,e=_choice(o,x,y)
   if isinstance(t,dict) and t.get('kind')=='WEED':out.append((0,x,y,['DIG'],'clear'))
   elif t is None:out.append((3,x,y,['PLANT',crop],e))
   elif isinstance(t,dict) and t.get('kind')=='PLANT':
    tc=str(t.get('crop'));age=day-int(t.get('planted_day',day) or day);mature=int(t.get('yield_units',0) or 0)>0 and (age>=_FIRST.get(tc,99) if _FULL else True)
    if mature:out.append((0,x,y,['HARVEST'],'mature_harvest'))
    elif not t.get('watered_today') and age<=_MAX.get(tc,99):out.append((1,x,y,['WATER'],'maintenance'))
 return out
def _toward(p,t):
 if p[0]<t[0]:return ['EAST']
 if p[0]>t[0]:return ['WEST']
 if p[1]<t[1]:return ['SOUTH']
 if p[1]>t[1]:return ['NORTH']
 return ['PASS']
def _units(o,st):
 ps=_pos(o);ts=_tasks(o);seeds={k:int(v or 0) for k,v in dict(_g(_g(o,'private',{}) or {},'seeds',{}) or {}).items()};pairs=sorted((t[0],abs(p[0]-t[1])+abs(p[1]-t[2]),i,j) for i,p in enumerate(ps) for j,t in enumerate(ts));ui=set();uj=set();a={}
 for _,_,i,j in pairs:
  if i not in ui and j not in uj:ui.add(i);uj.add(j);a[i]=j
 out=[]
 for i,p in enumerate(ps):
  if i not in a:out.append(['PASS']);_rec(st,'safe_idle');continue
  t=ts[a[i]];act=list(t[3]) if p==(t[1],t[2]) else _toward(p,(t[1],t[2]));e=t[4] if p==(t[1],t[2]) else 'logistics'
  if act[0]=='PLANT':
   if seeds.get(act[1],0)<=0:act=['PASS'];e='safe_idle'
   else:seeds[act[1]]-=1
  out.append(act);_rec(st,e)
 return out
def _market(o,st):
 f=_farm(o);p=_g(o,'private',{}) or {};shed={k:int(v or 0) for k,v in dict(_g(p,'shed',{}) or {}).items()};seeds={k:int(v or 0) for k,v in dict(_g(p,'seeds',{}) or {}).items()};orders=[]
 for item,q in shed.items():
  if q>0 and item not in {'GOOSE','COW','SHEEP'}:orders.append(['SELL',item,q]);_rec(st,'liquidate')
 hands=len(list(_g(f,'hands',[]) or []));desired=12 if int(_g(f,'money',0) or 0)>5000 else 8
 for _ in range(max(0,min(desired-hands,10-len(orders)))):orders.append(['HIRE']);_rec(st,'labor_budget')
 money=int(_g(f,'money',0) or 0);qds=len(list(_g(f,'unlocked_quadrants',[]) or []));cost=(1000,2000,4000)
 if qds<4 and len(orders)<10 and money>=cost[qds-1]+500:orders.append(['BUY_LAND']);_rec(st,'land_budget')
 need={c:0 for c in _CROPS}
 for _,_,_,a,_ in _tasks(o):
  if a[0]=='PLANT':need[a[1]]+=1
 for c in _CROPS:
  q=max(0,min(need[c]-seeds.get(c,0),15))
  if q and len(orders)<10:orders.append(['BUY_SEED',c,q]);_rec(st,'seed_budget')
 return orders[:10]
def _reset(o):
 s,step=_seat(o),_step(o);st=_STATE[s]
 if step==0 or step<int(st.get('last',-1)):st.clear();st.update(last=step,calls=0,experts={},fallback=0,changed_calls=0)
 st['last']=step;st['calls']=int(st.get('calls',0))+1;return st
def _fallback(o):return {'farmer':['PASS'],'hands':[['PASS'] for _ in list(_g(_farm(o),'hands',[]) or [])],'market':[]}
def model_status():return {'kind':'v99_maturity_clock_temporal_petri_moe','model_id':'v99_maturity_clock_temporal_petri_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','mode':'full' if _FULL else 'ablation','router':'crop-age-temporal-petri-router','experts':['feed_grain','quick_root','demand_perennial','premium_melon','terminal_quick','clear','maintenance','mature_harvest','logistics','liquidate','labor_budget','land_budget','seed_budget'],'stats':copy.deepcopy(_STATE)}
def agent(obs,configuration=None):
 del configuration
 try:
  st=_reset(obs);u=_units(obs,st);return {'farmer':u[0],'hands':u[1:],'market':_market(obs,st)}
 except Exception:_STATE[_seat(obs)]['fallback']=int(_STATE[_seat(obs)].get('fallback',0))+1;return _fallback(obs)
