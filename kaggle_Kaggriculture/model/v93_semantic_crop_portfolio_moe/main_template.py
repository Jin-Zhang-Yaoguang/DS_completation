"""Standalone semantic crop portfolio Hierarchical MoE."""
import base64, copy, json, zlib

__version__='v93-semantic-crop-portfolio-moe-rc1'
_MODE='__MODE__'; _FULL=_MODE=='full'
_FRAMES=json.loads(zlib.decompress(base64.b85decode('__PAYLOAD__')).decode())['frames']
_CROPS=('WHEAT','CARROT','TOMATO','STRAWBERRY','MELON')
_SHOP_CROPS={
 'BAKERY':{'WHEAT'},'BRUNCH_SPOT':{'WHEAT','STRAWBERRY'},
 'FARMERS_MARKET':{'WHEAT','CARROT','TOMATO','STRAWBERRY'},
 'ICE_CREAM_SHOP':{'WHEAT','STRAWBERRY'},'PET_CAFE':{'CARROT'},
 'PIZZA_SHOP':{'WHEAT','TOMATO'},'SMOOTHIE_SHOP':{'STRAWBERRY'},'YARN_STORE':set(),
}
_COST={'WHEAT':10,'CARROT':20,'TOMATO':50,'STRAWBERRY':100,'MELON':80}
_MATURITY={'WHEAT':4,'CARROT':3,'TOMATO':8,'STRAWBERRY':10,'MELON':12}
_YIELD={'WHEAT':6,'CARROT':4,'TOMATO':4,'STRAWBERRY':4,'MELON':6}
_STATE={0:{'last':-1,'calls':0,'mapping':{},'experts':{},'rerouted_plants':0,'fallback':0},1:{'last':-1,'calls':0,'mapping':{},'experts':{},'rerouted_plants':0,'fallback':0}}

def _get(v,k,d=None):
    if isinstance(v,dict): return v.get(k,d)
    g=getattr(v,'get',None); return g(k,d) if callable(g) else getattr(v,k,d)
def _seat(o): return 1 if int(_get(o,'player',0) or 0)==1 else 0
def _step(o):
    x=_get(o,'step',None); return min(718,max(0,int(x if x is not None else int(_get(o,'day',0) or 0)*24+int(_get(o,'hour',0) or 0))))
def _farm(o):
    fs=list(_get(o,'farms',[]) or []); s=_seat(o); return fs[s] if s<len(fs) else {}
def _private(o): return _get(o,'private',{}) or {}
def _record(o,e):
    d=_STATE[_seat(o)]['experts']; d[e]=int(d.get(e,0))+1

def _choose(o,source):
    if source=='WHEAT': return 'WHEAT','feed_grain'
    remaining=30-int(_get(o,'day',0) or 0)
    if remaining<5: return ('CARROT' if remaining>=3 else 'WHEAT'),'terminal_quick'
    shops=set(_get(_get(o,'town',{}) or {},'unlocked_shops',[]) or [])
    demanded=set()
    for shop in shops: demanded.update(_SHOP_CROPS.get(str(shop),set()))
    prices=dict(_get(_get(o,'market',{}) or {},'prices',{}) or {})
    candidates=[c for c in _CROPS if _MATURITY[c]<=remaining]
    scored=[]
    for crop in candidates:
        demand=1.8 if crop in demanded else 1.0
        value=max(1,int(prices.get(crop,1) or 1))*_YIELD[crop]*demand/(_COST[crop]+8*_MATURITY[crop])
        scored.append((value,crop))
    chosen=max(scored)[1]
    expert='demand_perennial' if chosen in demanded and chosen in {'TOMATO','STRAWBERRY'} else 'quick_root' if chosen=='CARROT' else 'premium_melon' if chosen=='MELON' else 'feed_grain'
    return chosen,expert

def _mapped(o,source):
    if not _FULL or source not in _CROPS: return source,'fixed_crop'
    state=_STATE[_seat(o)]; mapping=state['mapping']
    if source not in mapping or (_step(o)%24==0 and _step(o)>=72): mapping[source]=_choose(o,source)[0]
    chosen=mapping[source]; _,expert=_choose(o,source)
    return chosen,expert

def _cap_market(o,orders):
    shed={k:max(0,int(v or 0)) for k,v in dict(_get(_private(o),'shed',{}) or {}).items()}
    seeds={k:max(0,int(v or 0)) for k,v in dict(_get(_private(o),'seeds',{}) or {}).items()}
    out=[]
    for raw in orders[:10]:
        order=list(raw); op=str(order[0]) if order else ''
        if op in {'BUY_SEED','SELL'} and len(order)>=3 and str(order[1]) in _CROPS:
            source=str(order[1]); chosen,expert=_mapped(o,source); order[1]=chosen; _record(o,expert)
            if op=='SELL':
                qty=min(max(0,int(order[2] or 0)),shed.get(chosen,0)); shed[chosen]=max(0,shed.get(chosen,0)-qty)
                if qty<=0 and source!=chosen and shed.get(source,0)>0: chosen=source; qty=min(max(0,int(order[2] or 0)),shed[source]); shed[source]-=qty; order[1]=source
                if qty<=0: continue
                order[2]=qty
            else:
                order[2]=max(0,int(order[2] or 0)); seeds[chosen]=seeds.get(chosen,0)+order[2]
        out.append(order)
    return out

def _reset(o):
    s,step=_seat(o),_step(o); st=_STATE[s]
    if step==0 or step<int(st.get('last',-1)): st.clear(); st.update(last=step,calls=0,mapping={},experts={},rerouted_plants=0,fallback=0)
    st['last']=step; st['calls']=int(st.get('calls',0))+1
def _fallback(o): return {'farmer':['PASS'],'hands':[['PASS'] for _ in list(_get(_farm(o),'hands',[]) or [])],'market':[]}
def model_status(): return {'kind':'v93_semantic_crop_portfolio_moe','model_id':'v93_semantic_crop_portfolio_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','mode':_MODE,'router':'shop-price-maturity-crop-router','experts':['feed_grain','quick_root','demand_perennial','premium_melon','terminal_quick'],'stats':copy.deepcopy(_STATE)}

def agent(obs,configuration=None):
    del configuration
    try:
        _reset(obs); frame=copy.deepcopy(_FRAMES[_step(obs)]); expected=len(list(_get(_farm(obs),'hands',[]) or []))
        orders=[list(frame.get('farmer') or ['PASS']),*[list(x or ['PASS']) for x in frame.get('hands',[])]]
        orders.extend([['PASS'] for _ in range(max(0,expected+1-len(orders)))]); orders=orders[:expected+1]
        seeds={k:max(0,int(v or 0)) for k,v in dict(_get(_private(obs),'seeds',{}) or {}).items()}
        if _FULL:
            for i,order in enumerate(orders):
                if len(order)>=2 and order[0]=='PLANT' and str(order[1]) in _CROPS:
                    source=str(order[1]); chosen,expert=_mapped(obs,source)
                    if seeds.get(chosen,0)<=0: chosen=source
                    if chosen!=source: _STATE[_seat(obs)]['rerouted_plants']+=1
                    if seeds.get(chosen,0)>0: seeds[chosen]-=1; order[1]=chosen
                    _record(obs,expert)
        market=_cap_market(obs,[list(x) for x in frame.get('market',[]) if x]) if _FULL else [list(x) for x in frame.get('market',[]) if x][:10]
        return {'farmer':orders[0],'hands':orders[1:],'market':market}
    except Exception:
        _STATE[_seat(obs)]['fallback']+=1; return _fallback(obs)
