"""Standalone legality-consensus-veto Hierarchical MoE."""
import base64,copy,json,zlib
__version__='v101-legality-consensus-veto-moe-rc1';_FULL='__MODE__'=='full';_P=json.loads(zlib.decompress(base64.b85decode('__PAYLOAD__')).decode());_R=_P['routes'];_BASE=_P['base'];_MOVE={'NORTH':(0,-1),'SOUTH':(0,1),'EAST':(1,0),'WEST':(-1,0)};_ACCESS={(4,4),(5,4),(4,5),(5,5)};_STATE={0:{},1:{}}
def _g(v,k,d=None):
 if isinstance(v,dict):return v.get(k,d)
 f=getattr(v,'get',None);return f(k,d) if callable(f) else getattr(v,k,d)
def _seat(o):return int(_g(o,'player',0) or 0)
def _step(o):return min(718,max(0,int(_g(o,'step',0) or 0)))
def _farm(o):return list(_g(o,'farms',[]) or [])[_seat(o)]
def _pos(o):
 f=_farm(o);return [tuple(map(int,_g(f,'farmer',[4,4]))),*[tuple(map(int,p)) for p in list(_g(f,'hands',[]) or [])]]
def _inv(o,n):
 x=[dict(v or {}) for v in list(_g(_g(o,'private',{}) or {},'inventories',[]) or [])];x.extend({} for _ in range(max(0,n-len(x))));return x[:n]
def _tile(o,p):
 try:
  x,y=p;r=list(_g(_farm(o),'tiles',[]) or []);return r[y][x] if 0<=y<len(r) and 0<=x<len(r[y]) else 'LOCKED'
 except:return 'LOCKED'
def _valid(o,i,a):
 if not a or a[0]=='PASS':return True
 ps=_pos(o)
 if i>=len(ps):return False
 p=ps[i];t=_tile(o,p);inv=_inv(o,len(ps))[i];pr=_g(o,'private',{}) or {};shed=dict(_g(pr,'shed',{}) or {});seed=dict(_g(pr,'seeds',{}) or {});op=str(a[0])
 if op in _MOVE:
  dx,dy=_MOVE[op];rows=list(_g(_farm(o),'tiles',[]) or []);return 0<=p[1]+dy<len(rows) and 0<=p[0]+dx<len(rows[p[1]+dy])
 if op=='DIG':return t!='LOCKED' and not(isinstance(t,dict) and t.get('animal'))
 if op=='PLANT':return t is None and len(a)>1 and int(seed.get(a[1],0) or 0)>0
 if op=='WATER':return isinstance(t,dict) and t.get('kind')=='PLANT' and not t.get('watered_today')
 if op=='HARVEST':return isinstance(t,dict) and int(t.get('yield_units',0) or 0)>0 and int(_g(o,'day',0) or 0)-int(t.get('planted_day',0) or 0)>= {'WHEAT':2,'CARROT':2,'TOMATO':8,'STRAWBERRY':10,'MELON':10}.get(str(t.get('crop')),0)
 if op=='FERTILIZE':return isinstance(t,dict) and t.get('kind')=='PLANT' and int(inv.get('FERTILIZER',0) or 0)>0
 if op in {'BUILD_COOP','BUILD_PASTURE'}:return t is None
 if op=='FEED':return isinstance(t,dict) and bool(t.get('animal')) and not t.get('fed_today') and int(inv.get('WHEAT',0) or 0)>0
 if op=='CARE':return isinstance(t,dict) and bool(t.get('animal')) and not t.get('cared_today')
 if op=='COLLECT_FERTILIZER':return isinstance(t,dict) and bool(t.get('fertilizer_available'))
 if op=='PICKUP':return p in _ACCESS and len(a)>2 and int(shed.get(a[1],0) or 0)>0
 if op=='DROP':return p in _ACCESS and sum(int(v or 0) for v in inv.values())>0
 if op=='PLACE':return len(a)>1 and int(inv.get(a[1],0) or 0)>0
 return False
def _key(a):return tuple(a[:2]) if a and a[0] in {'PLANT','PICKUP','PLACE','FEED'} else tuple(a)
def _rec(st,e):st['experts'][e]=int(st['experts'].get(e,0))+1
def _reset(o):
 s,step=_seat(o),_step(o);st=_STATE[s]
 if step==0 or step<int(st.get('last',-1)):st.clear();st.update(last=step,calls=0,experts={},recoveries=0,changed_calls=0,fallback=0)
 st['last']=step;st['calls']=int(st.get('calls',0))+1;return st
def _fallback(o):return {'farmer':['PASS'],'hands':[['PASS'] for _ in list(_g(_farm(o),'hands',[]) or [])],'market':[]}
def model_status():return {'kind':'v101_legality_consensus_veto_moe','model_id':'v101_legality_consensus_veto_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','mode':'full' if _FULL else 'ablation','router':'illegal-action-independent-expert-consensus','experts':['base_direct','consensus_recovery','safe_idle',*list(_R)],'stats':copy.deepcopy(_STATE)}
def agent(obs,configuration=None):
 del configuration
 try:
  st=_reset(obs);step=_step(obs);n=len(list(_g(_farm(obs),'hands',[]) or []));streams={e:[list(_R[e][step].get('farmer') or ['PASS']),*[list(x or ['PASS']) for x in _R[e][step].get('hands',[])]] for e in _R};out=[]
  for i in range(n+1):
   base=streams[_BASE][i] if i<len(streams[_BASE]) else ['PASS']
   if not _FULL or _valid(obs,i,base):out.append(base);_rec(st,'base_direct');continue
   votes={}
   for e,s in streams.items():
    if e==_BASE or i>=len(s) or not _valid(obs,i,s[i]):continue
    k=_key(s[i]);votes.setdefault(k,[]).append((e,s[i]))
   best=max(votes.values(),key=lambda z:(len(z),z[0][0])) if votes else []
   if len(best)>=2:out.append(list(best[0][1]));st['recoveries']+=1;_rec(st,'consensus_recovery');[_rec(st,'source:'+e) for e,_ in best]
   else:out.append(['PASS']);_rec(st,'safe_idle')
  st['changed_calls']+=int(out!=streams[_BASE][:n+1]);m=_R[_BASE][step];return {'farmer':out[0],'hands':out[1:],'market':[list(x) for x in m.get('market',[]) if x][:10]}
 except Exception:_STATE[_seat(obs)]['fallback']=int(_STATE[_seat(obs)].get('fallback',0))+1;return _fallback(obs)
