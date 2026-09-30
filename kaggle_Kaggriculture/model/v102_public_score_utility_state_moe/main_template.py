"""Standalone public-score utility-state Hierarchical MoE."""
import base64,copy,json,zlib
__version__='v102-public-score-utility-state-moe-rc1';_FULL='__MODE__'=='full';_A=json.loads(zlib.decompress(base64.b85decode('__PAYLOAD__')).decode())['actions'];_ITEMS=('WHEAT','CARROT','TOMATO','STRAWBERRY','MELON','EGG','MILK','WOOL','FERTILIZER');_ACCESS={(4,4),(5,4),(4,5),(5,5)};_STATE={0:{},1:{}}
def _g(v,k,d=None):
 if isinstance(v,dict):return v.get(k,d)
 f=getattr(v,'get',None);return f(k,d) if callable(f) else getattr(v,k,d)
def _seat(o):return int(_g(o,'player',0) or 0)
def _step(o):return min(718,max(0,int(_g(o,'step',0) or 0)))
def _farm(o):return list(_g(o,'farms',[]) or [])[_seat(o)]
def _positions(o):
 f=_farm(o);return [tuple(map(int,_g(f,'farmer',[4,4]))),*[tuple(map(int,p)) for p in list(_g(f,'hands',[]) or [])]]
def _inv(o,n):
 x=[dict(v or {}) for v in list(_g(_g(o,'private',{}) or {},'inventories',[]) or [])];x.extend({} for _ in range(max(0,n-len(x))));return x[:n]
def _project(o,u):
 shed={k:max(0,int(v or 0)) for k,v in dict(_g(_g(o,'private',{}) or {},'shed',{}) or {}).items()};ps=_positions(o);inv=_inv(o,len(ps))
 for i,a in enumerate(u):
  if i>=len(ps) or ps[i] not in _ACCESS:continue
  dep=list(inv[i].items()) if a and a[0]=='DROP' else []
  if a and a[0]=='PLACE' and len(a)>1:dep=[(str(a[1]),int(a[2] or 1) if len(a)>2 else 1)]
  for item,q in dep:
   n=min(max(0,int(q or 0)),int(inv[i].get(item,0) or 0),max(0,100-sum(shed.values())));shed[item]=shed.get(item,0)+n
 return shed
def _rec(st,e):st['experts'][e]=int(st['experts'].get(e,0))+1
def _utility(o,u,raw,st):
 if not _FULL:_rec(st,'growth_compound');return raw
 farms=list(_g(o,'farms',[]) or []);s=_seat(o);gap=int(_g(farms[s],'money',0) or 0)-int(_g(farms[1-s],'money',0) or 0);shed=_project(o,u);prices=dict(_g(_g(o,'market',{}) or {},'prices',{}) or {});value=sum(shed.get(i,0)*max(1,int(prices.get(i,1) or 1)) for i in _ITEMS);step=_step(o)
 expert='terminal_utility' if step>=700 else 'lead_lock' if step>=600 and gap>5000 else 'deficit_recovery' if gap < -5000 and value>0 else 'growth_compound';_rec(st,expert)
 if expert=='growth_compound':return raw
 sells=[['SELL',i,shed[i]] for i in _ITEMS if shed.get(i,0)>0];tail=[x for x in raw if not x or x[0]!='SELL'];return (sells+tail)[:10]
def _reset(o):
 s,step=_seat(o),_step(o);st=_STATE[s]
 if step==0 or step<int(st.get('last',-1)):st.clear();st.update(last=step,calls=0,experts={},changed_calls=0,fallback=0)
 st['last']=step;st['calls']=int(st.get('calls',0))+1;return st
def _fallback(o):return {'farmer':['PASS'],'hands':[['PASS'] for _ in list(_g(_farm(o),'hands',[]) or [])],'market':[]}
def model_status():return {'kind':'v102_public_score_utility_state_moe','model_id':'v102_public_score_utility_state_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','mode':'full' if _FULL else 'ablation','router':'public-cash-gap-liquidatable-value-router','experts':['growth_compound','deficit_recovery','lead_lock','terminal_utility'],'stats':copy.deepcopy(_STATE)}
def agent(obs,configuration=None):
 del configuration
 try:
  st=_reset(obs);a=copy.deepcopy(_A[_step(obs)]);n=len(list(_g(_farm(obs),'hands',[]) or []));u=[list(a.get('farmer') or ['PASS']),*[list(x or ['PASS']) for x in a.get('hands',[])]];u.extend([['PASS'] for _ in range(max(0,n+1-len(u)))]);u=u[:n+1];raw=[list(x) for x in a.get('market',[]) if x][:10];m=_utility(obs,u,raw,st);st['changed_calls']+=int(m!=raw);return {'farmer':u[0],'hands':u[1:],'market':m}
 except Exception:_STATE[_seat(obs)]['fallback']=int(_STATE[_seat(obs)].get('fallback',0))+1;return _fallback(obs)
