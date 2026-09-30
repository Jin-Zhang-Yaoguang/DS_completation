"""Standalone path-invariant control-barrier Hierarchical MoE."""
import base64,copy,json,zlib
__version__='v95-path-invariant-control-barrier-moe-rc1';_MODE='__MODE__';_FULL=_MODE=='full';_FRAMES=json.loads(zlib.decompress(base64.b85decode('__PAYLOAD__')).decode())['frames'];_ACCESS={(4,4),(5,4),(4,5),(5,5)};_MOVES={'NORTH':(0,-1),'SOUTH':(0,1),'EAST':(1,0),'WEST':(-1,0)};_PRODUCTS=('WHEAT','CARROT','TOMATO','STRAWBERRY','MELON','EGG','MILK','WOOL','FERTILIZER')
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
def _tile(o,p):
 try:
  x,y=p;rows=list(_get(_farm(o),'tiles',[]) or []);return rows[y][x] if 0<=y<len(rows) and 0<=x<len(rows[y]) else 'LOCKED'
 except (IndexError,TypeError,ValueError):return 'LOCKED'
def _record(o,e):
 d=_STATE[_seat(o)]['experts'];d[e]=int(d.get(e,0))+1
def _valid(o,i,a,seeds,shed):
 if not a or a[0]=='PASS':return True
 ps=_positions(o)
 if i>=len(ps):return False
 p=ps[i];t=_tile(o,p);inv=_inventories(o,len(ps))[i];op=str(a[0])
 if op in _MOVES:
  dx,dy=_MOVES[op];rows=list(_get(_farm(o),'tiles',[]) or []);return 0<=p[1]+dy<len(rows) and 0<=p[0]+dx<len(rows[p[1]+dy])
 if op=='DIG':return t!='LOCKED' and not(isinstance(t,dict) and t.get('animal'))
 if op=='PLANT':return t is None and len(a)>1 and seeds.get(a[1],0)>0
 if op=='WATER':return isinstance(t,dict) and t.get('kind')=='PLANT' and not t.get('watered_today')
 if op=='HARVEST':return isinstance(t,dict) and int(t.get('yield_units',0) or 0)>0
 if op=='FERTILIZE':return isinstance(t,dict) and t.get('kind')=='PLANT' and int(inv.get('FERTILIZER',0) or 0)>0
 if op in {'BUILD_COOP','BUILD_PASTURE'}:return t is None
 if op=='FEED':return isinstance(t,dict) and bool(t.get('animal')) and not t.get('fed_today') and int(inv.get('WHEAT',0) or 0)>0
 if op=='CARE':return isinstance(t,dict) and bool(t.get('animal')) and not t.get('cared_today')
 if op=='COLLECT_FERTILIZER':return isinstance(t,dict) and bool(t.get('fertilizer_available'))
 if op=='PICKUP':return p in _ACCESS and len(a)>2 and shed.get(a[1],0)>0
 if op=='DROP':return p in _ACCESS and sum(max(0,int(v or 0)) for v in inv.values())>0
 if op=='PLACE':return len(a)>1 and int(inv.get(a[1],0) or 0)>0
 return False
def _shield(o,orders):
 private=_get(o,'private',{}) or {};seeds={k:max(0,int(v or 0)) for k,v in dict(_get(private,'seeds',{}) or {}).items()};shed={k:max(0,int(v or 0)) for k,v in dict(_get(private,'shed',{}) or {}).items()};out=[]
 for i,raw in enumerate(orders):
  a=list(raw);expert='direct_task'
  if not _valid(o,i,a,seeds,shed):
   t=_tile(o,_positions(o)[i]);op=str(a[0]) if a else 'PASS'
   if op in {'PLANT','BUILD_COOP','BUILD_PASTURE'} and isinstance(t,dict) and t.get('kind')=='WEED':a=['DIG'];expert='same_tile_prerequisite'
   else:a=['PASS'];expert='safe_idle'
  elif len(a)>=2 and a[0]=='PLANT':seeds[a[1]]-=1
  elif len(a)>=3 and a[0]=='PICKUP':
   q=min(max(0,int(a[2] or 0)),shed.get(a[1],0));shed[a[1]]=max(0,shed.get(a[1],0)-q);a=['PICKUP',a[1],q] if q else ['PASS'];expert='resource_cap'
  _record(o,expert);out.append(a)
 return out
def _market(o,raw,unit_orders):
 shed={k:max(0,int(v or 0)) for k,v in dict(_get(_get(o,'private',{}) or {},'shed',{}) or {}).items()};positions=_positions(o);inventories=_inventories(o,len(positions));out=[]
 for i,a in enumerate(unit_orders):
  if i>=len(positions) or positions[i] not in _ACCESS:continue
  deposits=list(inventories[i].items()) if a and a[0]=='DROP' else []
  if a and a[0]=='PLACE' and len(a)>1:deposits=[(str(a[1]),int(a[2] or 1) if len(a)>2 else 1)]
  for item,q in deposits:
   x=min(max(0,int(q or 0)),int(inventories[i].get(item,0) or 0),max(0,100-sum(shed.values())));shed[item]=shed.get(item,0)+x
 for x in raw[:10]:
  a=list(x)
  if len(a)>=3 and a[0]=='SELL':
   q=min(max(0,int(a[2] or 0)),shed.get(a[1],0));shed[a[1]]=max(0,shed.get(a[1],0)-q)
   if q<=0:continue
   a[2]=q;_record(o,'resource_cap')
  out.append(a)
 if _step(o)>=715:
  sold={str(a[1]):int(a[2]) for a in out if len(a)>=3 and a[0]=='SELL'}
  for item in _PRODUCTS:
   q=max(0,shed.get(item,0)-sold.get(item,0))
   if q and len(out)<10:out.append(['SELL',item,q]);_record(o,'terminal_liquidation')
 return out[:10]
def _reset(o):
 s,st=_seat(o),_step(o);d=_STATE[s]
 if st==0 or st<int(d.get('last',-1)):d.clear();d.update(last=st,calls=0,changed_calls=0,experts={},fallback=0)
 d['last']=st;d['calls']=int(d.get('calls',0))+1
def _fallback(o):return {'farmer':['PASS'],'hands':[['PASS'] for _ in list(_get(_farm(o),'hands',[]) or [])],'market':[]}
def model_status():return {'kind':'v95_path_invariant_control_barrier_moe','model_id':'v95_path_invariant_control_barrier_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','mode':_MODE,'router':'hard-precondition-control-barrier','experts':['direct_task','same_tile_prerequisite','resource_cap','safe_idle','terminal_liquidation'],'stats':copy.deepcopy(_STATE)}
def agent(obs,configuration=None):
 del configuration
 try:
  _reset(obs);f=copy.deepcopy(_FRAMES[_step(obs)]);n=len(list(_get(_farm(obs),'hands',[]) or []));raw=[list(f.get('farmer') or ['PASS']),*[list(x or ['PASS']) for x in f.get('hands',[])]];raw.extend([['PASS'] for _ in range(max(0,n+1-len(raw)))]);raw=raw[:n+1];rm=[list(x) for x in f.get('market',[]) if x][:10]
  if _FULL:orders=_shield(obs,raw);market=_market(obs,rm,orders)
  else:orders=raw;market=rm
  if orders!=raw or market!=rm:_STATE[_seat(obs)]['changed_calls']+=1
  return {'farmer':orders[0],'hands':orders[1:],'market':market}
 except Exception:_STATE[_seat(obs)]['fallback']+=1;return _fallback(obs)
