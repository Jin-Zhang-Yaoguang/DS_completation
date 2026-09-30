"""Standalone seat-priority robust-route Hierarchical MoE."""
import base64,copy,json,zlib
__version__='v96-seat-priority-robust-route-moe-rc1';_MODE='__MODE__';_FULL=_MODE=='full';_ROUTES=json.loads(zlib.decompress(base64.b85decode('__PAYLOAD__')).decode());_STATE={0:{'last':-1,'calls':0,'experts':{},'changed_calls':0,'fallback':0},1:{'last':-1,'calls':0,'experts':{},'changed_calls':0,'fallback':0}}
def _get(v,k,d=None):
 if isinstance(v,dict):return v.get(k,d)
 g=getattr(v,'get',None);return g(k,d) if callable(g) else getattr(v,k,d)
def _seat(o):return 1 if int(_get(o,'player',0) or 0)==1 else 0
def _step(o):
 x=_get(o,'step',None);return min(718,max(0,int(x if x is not None else int(_get(o,'day',0) or 0)*24+int(_get(o,'hour',0) or 0))))
def _farm(o):
 fs=list(_get(o,'farms',[]) or []);s=_seat(o);return fs[s] if s<len(fs) else {}
def _record(o,e):
 d=_STATE[_seat(o)]['experts'];d[e]=int(d.get(e,0))+1
def _reset(o):
 s,st=_seat(o),_step(o);d=_STATE[s]
 if st==0 or st<int(d.get('last',-1)):d.clear();d.update(last=st,calls=0,experts={},changed_calls=0,fallback=0)
 d['last']=st;d['calls']=int(d.get('calls',0))+1
def _fallback(o):return {'farmer':['PASS'],'hands':[['PASS'] for _ in list(_get(_farm(o),'hands',[]) or [])],'market':[]}
def model_status():return {'kind':'v96_seat_priority_robust_route_moe','model_id':'v96_seat_priority_robust_route_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','mode':_MODE,'router':'immutable-seat-priority-router','experts':['robust_first_mover','upside_second_mover','arity_safe_executor'],'stats':copy.deepcopy(_STATE)}
def agent(obs,configuration=None):
 del configuration
 try:
  _reset(obs);seat=_seat(obs);route='upside' if _FULL and seat==1 else 'robust';expert='upside_second_mover' if route=='upside' else 'robust_first_mover';_record(obs,expert);a=copy.deepcopy(_ROUTES[route][_step(obs)]);n=len(list(_get(_farm(obs),'hands',[]) or []));hands=[list(x or ['PASS']) for x in a.get('hands',[])][:n];hands.extend([['PASS'] for _ in range(max(0,n-len(hands)))]);_record(obs,'arity_safe_executor')
  if _FULL and route=='upside':_STATE[seat]['changed_calls']+=1
  return {'farmer':list(a.get('farmer') or ['PASS']),'hands':hands,'market':[list(x) for x in a.get('market',[]) if x][:10]}
 except Exception:_STATE[_seat(obs)]['fallback']+=1;return _fallback(obs)
