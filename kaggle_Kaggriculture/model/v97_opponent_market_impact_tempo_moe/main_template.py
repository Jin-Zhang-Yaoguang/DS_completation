"""Standalone opponent-market-impact tempo Hierarchical MoE."""
import base64,copy,json,zlib
__version__='v97-opponent-market-impact-tempo-moe-rc1';_MODE='__MODE__';_FULL=_MODE=='full';_P=json.loads(zlib.decompress(base64.b85decode('__PAYLOAD__')).decode());_A=_P['actions'];_T=_P['tree'];_ITEMS=('WHEAT','CARROT','TOMATO','STRAWBERRY','MELON','EGG','MILK','WOOL','FERTILIZER');_SHOPS=('BAKERY','BRUNCH_SPOT','FARMERS_MARKET','ICE_CREAM_SHOP','PET_CAFE','PIZZA_SHOP','SMOOTHIE_SHOP','YARN_STORE')
_CROP={'PLANT','WATER','HARVEST','FERTILIZE','DIG'};_ANIMAL={'BUILD_COOP','BUILD_PASTURE','FEED','CARE','COLLECT_FERTILIZER'};_STATE={0:{},1:{}}
def _get(v,k,d=None):
 if isinstance(v,dict):return v.get(k,d)
 g=getattr(v,'get',None);return g(k,d) if callable(g) else getattr(v,k,d)
def _seat(o):return 1 if int(_get(o,'player',0) or 0)==1 else 0
def _step(o):
 x=_get(o,'step',None);return min(718,max(0,int(x if x is not None else int(_get(o,'day',0) or 0)*24+int(_get(o,'hour',0) or 0))))
def _farm(o):
 fs=list(_get(o,'farms',[]) or []);s=_seat(o);return fs[s] if s<len(fs) else {}
def _signed(a,item):
 v=0;slot=10
 for i,x in enumerate((a or {}).get('market',[]) or []):
  if len(x)<3 or str(x[1])!=item:continue
  if x[0]=='SELL':v+=max(0,int(x[2] or 0));slot=min(slot,i)
  elif x[0]=='BUY_PRODUCT':v-=max(0,int(x[2] or 0));slot=min(slot,i)
 return v,slot
def _tree(x):
 n=0
 while _T['left'][n]>=0:n=_T['left'][n] if x[_T['feature'][n]]<=_T['threshold'][n] else _T['right'][n]
 values=_T['value'][n];return _T['classes'][max(range(len(values)),key=lambda i:values[i])]
def _record(st,e,n=1):st['experts'][e]=int(st['experts'].get(e,0))+n
def _infer(o,st):
 if st.get('prev_inv') is None:return {x:0 for x in _ITEMS}
 curi=_get(_get(o,'market',{}) or {},'inventory',{}) or {};curp=_get(_get(o,'market',{}) or {},'prices',{}) or {};ps=st['prev_step'];shops=set(st['prev_shops']);out={}
 for j,item in enumerate(_ITEMS):
  own,slot=_signed(st['prev_action'],item);x=[int(curi[item])-int(st['prev_inv'][item]),int(curp[item])-int(st['prev_prices'][item]),own,slot,j,_seat(o),ps%4,ps%24,int(ps%4==0),int(ps%24==0),*[int(s in shops) for s in _SHOPS]];out[item]=_tree(x)
 return out
def _route_units(o,a,st):
 n=len(list(_get(_farm(o),'hands',[]) or []));orders=[list(a.get('farmer') or ['PASS']),*[list(x or ['PASS']) for x in a.get('hands',[])]];orders.extend([['PASS'] for _ in range(max(0,n+1-len(orders)))]);orders=orders[:n+1]
 for x in orders:
  op=str(x[0]) if x else 'PASS';_record(st,'crop_production' if op in _CROP else 'livestock_production' if op in _ANIMAL else 'logistics_execution')
 return orders
def _market(a,labels,st,step):
 raw=[list(x) for x in a.get('market',[]) if x][:10]
 if not _FULL:return raw
 has_purchase=any(x and x[0] in {'HIRE','BUY_LAND','BUY_SEED','BUY_PRODUCT','BUY_ANIMAL'} for x in raw);front=[];body=[]
 for x in raw:
  if len(x)>=3 and x[0]=='SELL':
   item=str(x[1]);lab=int(labels.get(item,0))
   if lab>0 and not has_purchase and step<712:st['dues'][item]=st['dues'].get(item,0)+max(0,int(x[2] or 0));_record(st,'one_step_wait');continue
   if lab<0:front.append(x);_record(st,'opponent_buy_preempt');continue
   _record(st,'same_slot_compete')
  body.append(x)
 for item,q in list(st['dues'].items()):
  if q>0:front.append(['SELL',item,q]);_record(st,'due_release')
 st['dues']={}
 return (front+body)[:10]
def _reset(o):
 s,step=_seat(o),_step(o);st=_STATE[s]
 if step==0 or step<int(st.get('last',-1)):st.clear();st.update(last=step,calls=0,experts={},dues={},prev_inv=None,prev_prices=None,prev_action={},prev_shops=[],prev_step=-1,fallback=0,changed_calls=0)
 st['last']=step;st['calls']=int(st.get('calls',0))+1;return st
def _fallback(o):return {'farmer':['PASS'],'hands':[['PASS'] for _ in list(_get(_farm(o),'hands',[]) or [])],'market':[]}
def model_status():return {'kind':'v97_opponent_market_impact_tempo_moe','model_id':'v97_opponent_market_impact_tempo_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','mode':_MODE,'router':'public-market-impact-shallow-tree','experts':['crop_production','livestock_production','logistics_execution','same_slot_compete','one_step_wait','opponent_buy_preempt','due_release'],'stats':copy.deepcopy(_STATE)}
def agent(obs,configuration=None):
 del configuration
 try:
  st=_reset(obs);step=_step(obs);labels=_infer(obs,st);a=copy.deepcopy(_A[step]);orders=_route_units(obs,a,st);raw=[list(x) for x in a.get('market',[]) if x][:10];market=_market(a,labels,st,step);st['changed_calls']+=int(market!=raw);m=_get(obs,'market',{}) or {};st['prev_inv']=dict(_get(m,'inventory',{}) or {});st['prev_prices']=dict(_get(m,'prices',{}) or {});st['prev_action']={'market':copy.deepcopy(market)};st['prev_shops']=list(_get(_get(obs,'town',{}) or {},'unlocked_shops',[]) or []);st['prev_step']=step;return {'farmer':orders[0],'hands':orders[1:],'market':market}
 except Exception:_STATE[_seat(obs)]['fallback']=int(_STATE[_seat(obs)].get('fallback',0))+1;return _fallback(obs)
