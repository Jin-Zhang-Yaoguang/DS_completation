"""Standalone market transaction DAG Hierarchical MoE."""
import base64,copy,json,zlib
__version__='v94-market-transaction-dag-moe-rc1';_MODE='__MODE__';_FULL=_MODE=='full';_FRAMES=json.loads(zlib.decompress(base64.b85decode('__PAYLOAD__')).decode())['frames']
_ACCESS={(4,4),(5,4),(4,5),(5,5)};_SEED={'WHEAT':10,'CARROT':20,'TOMATO':50,'STRAWBERRY':100,'MELON':80};_ANIMAL={'GOOSE':300,'COW':400,'SHEEP':500}
_STATE={0:{'last':-1,'calls':0,'changed_calls':0,'experts':{},'fallback':0},1:{'last':-1,'calls':0,'changed_calls':0,'experts':{},'fallback':0}}
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
def _inventories(o,n):
 vs=[dict(x or {}) for x in list(_get(_get(o,'private',{}) or {},'inventories',[]) or [])];vs.extend({} for _ in range(max(0,n-len(vs))));return vs[:n]
def _record(o,e):
 d=_STATE[_seat(o)]['experts'];d[e]=int(d.get(e,0))+1
def _fib(n):
 a,b=0,1
 for _ in range(max(0,int(n))):a,b=b,a+b
 return a
def _project(o,farmer,hands):
 p={k:max(0,int(v or 0)) for k,v in dict(_get(_get(o,'private',{}) or {},'shed',{}) or {}).items()};pos=_positions(o);inv=_inventories(o,len(pos))
 for i,order in enumerate([farmer,*hands]):
  if i>=len(pos) or pos[i] not in _ACCESS:continue
  deposits=list(inv[i].items()) if order and order[0]=='DROP' else []
  if order and order[0]=='PLACE' and len(order)>1:deposits=[(str(order[1]),int(order[2] or 1) if len(order)>2 else 1)]
  for item,q in deposits:
   x=min(max(0,int(q or 0)),int(inv[i].get(item,0) or 0),max(0,100-sum(p.values())));p[item]=p.get(item,0)+x
 return p
def _dag(o,orders,farmer,hands):
 farm=_farm(o);money=max(0,int(_get(farm,'money',0) or 0));hires=int(_get(farm,'hires_today',0) or 0);quads=len(list(_get(farm,'unlocked_quadrants',[]) or []));prices=dict(_get(_get(o,'market',{}) or {},'prices',{}) or {});shed=_project(o,farmer,hands);land=(1000,2000,4000)
 buckets={'liquidation':[],'production_input':[],'fixed_capital':[],'animal_expansion':[]}
 for x in orders[:10]:
  op=str(x[0]) if x else ''
  key='liquidation' if op=='SELL' else 'production_input' if op in {'BUY_SEED','BUY_PRODUCT'} else 'animal_expansion' if op=='BUY_ANIMAL' else 'fixed_capital';buckets[key].append(list(x))
 sequence=[]
 for expert in ('liquidation','production_input','fixed_capital','animal_expansion'):
  if buckets[expert]:_record(o,expert)
  for order in buckets[expert]:
   op=str(order[0]) if order else ''
   if op=='SELL' and len(order)>=3:
    item=str(order[1]);q=min(max(0,int(order[2] or 0)),shed.get(item,0));shed[item]=max(0,shed.get(item,0)-q)
    if q<=0:continue
    order[2]=q;money+=q*max(1,int(prices.get(item,1) or 1))
   elif op=='BUY_SEED' and len(order)>=3 and str(order[1]) in _SEED:
    item=str(order[1]);q=min(max(0,int(order[2] or 0)),money//_SEED[item]);
    if q<=0:continue
    order[2]=q;money-=q*_SEED[item]
   elif op=='BUY_PRODUCT' and len(order)>=3:
    item=str(order[1]);cost=max(1,int(prices.get(item,1) or 1));q=min(max(0,int(order[2] or 0)),money//cost,max(0,100-sum(shed.values())))
    if q<=0:continue
    order[2]=q;money-=q*cost;shed[item]=shed.get(item,0)+q
   elif op=='HIRE':
    c=_fib(hires)
    if money<c:continue
    money-=c;hires+=1
   elif op=='BUY_LAND':
    c=land[quads-1] if 0<=quads-1<len(land) else 10**18
    if money<c:continue
    money-=c;quads+=1
   elif op=='BUY_ANIMAL' and len(order)>=3 and str(order[1]) in _ANIMAL:
    item=str(order[1]);q=min(max(0,int(order[2] or 0)),money//_ANIMAL[item],max(0,100-sum(shed.values())))
    if q<=0:continue
    order[2]=q;money-=q*_ANIMAL[item]
   sequence.append(order)
 return sequence[:10]
def _reset(o):
 s,st=_seat(o),_step(o);d=_STATE[s]
 if st==0 or st<int(d.get('last',-1)):d.clear();d.update(last=st,calls=0,changed_calls=0,experts={},fallback=0)
 d['last']=st;d['calls']=int(d.get('calls',0))+1
def _fallback(o):return {'farmer':['PASS'],'hands':[['PASS'] for _ in list(_get(_farm(o),'hands',[]) or [])],'market':[]}
def model_status():return {'kind':'v94_market_transaction_dag_moe','model_id':'v94_market_transaction_dag_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','mode':_MODE,'router':'cash-inventory-dependency-dag','experts':['liquidation','production_input','fixed_capital','animal_expansion'],'stats':copy.deepcopy(_STATE)}
def agent(obs,configuration=None):
 del configuration
 try:
  _reset(obs);f=copy.deepcopy(_FRAMES[_step(obs)]);n=len(list(_get(_farm(obs),'hands',[]) or []));farmer=list(f.get('farmer') or ['PASS']);hands=[list(x or ['PASS']) for x in f.get('hands',[])][:n];hands.extend([['PASS'] for _ in range(max(0,n-len(hands)))]);raw=[list(x) for x in f.get('market',[]) if x][:10];market=_dag(obs,raw,farmer,hands) if _FULL else raw
  if market!=raw:_STATE[_seat(obs)]['changed_calls']+=1
  return {'farmer':farmer,'hands':hands,'market':market}
 except Exception:_STATE[_seat(obs)]['fallback']+=1;return _fallback(obs)
