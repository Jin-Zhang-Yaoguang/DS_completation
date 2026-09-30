"""Standalone factorized viability-kernel Hierarchical MoE."""
import base64,copy,json,zlib
__version__='v100-factorized-viability-kernel-moe-rc1';_FULL='__MODE__'=='full';_P=json.loads(zlib.decompress(base64.b85decode('__PAYLOAD__')).decode());_R=_P['routes'];_F=_P['refs'];_BASE=_P['base'];_STATE={0:{},1:{}}
def _g(v,k,d=None):
 if isinstance(v,dict):return v.get(k,d)
 f=getattr(v,'get',None);return f(k,d) if callable(f) else getattr(v,k,d)
def _seat(o):return int(_g(o,'player',0) or 0)
def _step(o):return min(718,max(0,int(_g(o,'step',0) or 0)))
def _farm(o):return list(_g(o,'farms',[]) or [])[_seat(o)]
def _feature(o):
 f=_farm(o);tiles=[t for row in list(_g(f,'tiles',[]) or []) for t in row];k={'EMPTY':sum(t is None for t in tiles),'WEED':sum(isinstance(t,dict) and t.get('kind')=='WEED' for t in tiles),'PLANT':sum(isinstance(t,dict) and t.get('kind')=='PLANT' for t in tiles)};c={x:sum(isinstance(t,dict) and t.get('crop')==x for t in tiles) for x in ('WHEAT','CARROT','TOMATO','STRAWBERRY','MELON')};p=_g(o,'private',{}) or {};shops=list(_g(_g(o,'town',{}) or {},'unlocked_shops',[]) or []);return {'shop':shops[0] if shops else 'NONE','quads':len(list(_g(f,'unlocked_quadrants',[]) or [])),'money':int(_g(f,'money',0) or 0),'kinds':k,'crops':c,'shed':{x:int(v or 0) for x,v in dict(_g(p,'shed',{}) or {}).items()},'seeds':{x:int(v or 0) for x,v in dict(_g(p,'seeds',{}) or {}).items()}}
def _dist(a,b,domain):
 d=50*int(a['shop']!=b['shop'])+10*abs(a['quads']-b['quads'])
 if domain=='unit':
  d+=sum(abs(a['kinds'].get(k,0)-b['kinds'].get(k,0)) for k in a['kinds']);d+=2*sum(abs(a['crops'].get(k,0)-b['crops'].get(k,0)) for k in a['crops'])
 else:
  d+=abs(a['money']-b['money'])/500;d+=sum(abs(a['shed'].get(k,0)-b['shed'].get(k,0)) for k in a['shed']);d+=sum(abs(a['seeds'].get(k,0)-b['seeds'].get(k,0)) for k in a['seeds'])
 return d
def _select(o,day,domain):
 if not _FULL:return _BASE
 a=_feature(o);return min(_R,key=lambda e:(_dist(a,_F[e][day],domain),e))
def _rec(st,e):st['experts'][e]=int(st['experts'].get(e,0))+1
def _reset(o):
 s,step=_seat(o),_step(o);st=_STATE[s]
 if step==0 or step<int(st.get('last',-1)):st.clear();st.update(last=step,calls=0,day=-1,unit=_BASE,market=_BASE,experts={},fallback=0,changed_calls=0)
 day=step//24
 if day!=st['day']:st['day']=day;st['unit']=_select(o,day,'unit');st['market']=_select(o,day,'market')
 st['last']=step;st['calls']=int(st.get('calls',0))+1;return st
def _fallback(o):return {'farmer':['PASS'],'hands':[['PASS'] for _ in list(_g(_farm(o),'hands',[]) or [])],'market':[]}
def model_status():return {'kind':'v100_factorized_viability_kernel_moe','model_id':'v100_factorized_viability_kernel_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','mode':'full' if _FULL else 'ablation','router':'day-boundary-factorized-viability-kernel','experts':list(_R),'stats':copy.deepcopy(_STATE)}
def agent(obs,configuration=None):
 del configuration
 try:
  st=_reset(obs);step=_step(obs);u=copy.deepcopy(_R[st['unit']][step]);m=copy.deepcopy(_R[st['market']][step]);n=len(list(_g(_farm(obs),'hands',[]) or []));hands=[list(x or ['PASS']) for x in u.get('hands',[])][:n];hands.extend([['PASS'] for _ in range(max(0,n-len(hands)))]) ;_rec(st,'unit:'+st['unit']);_rec(st,'market:'+st['market']);st['changed_calls']+=int(st['unit']!=_BASE or st['market']!=_BASE);return {'farmer':list(u.get('farmer') or ['PASS']),'hands':hands,'market':[list(x) for x in m.get('market',[]) if x][:10]}
 except Exception:_STATE[_seat(obs)]['fallback']=int(_STATE[_seat(obs)].get('fallback',0))+1;return _fallback(obs)
