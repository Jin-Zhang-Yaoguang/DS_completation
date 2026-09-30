"""Standalone conformal-support risk-option Hierarchical MoE."""
import base64,copy,json,zlib

__version__="v106-conformal-support-option-moe-rc1"
_FULL="__MODE__"=="full"
_DATA=json.loads(zlib.decompress(base64.b85decode("__PAYLOAD__")).decode())
_ACTIONS=_DATA["actions"]
_TARGETS=_DATA["targets"]
_ACCESS={(4,4),(5,4),(4,5),(5,5)}
_MOVES={"NORTH":(0,-1),"SOUTH":(0,1),"EAST":(1,0),"WEST":(-1,0)}
_SEED_COST={"WHEAT":10,"CARROT":20,"TOMATO":50,"STRAWBERRY":100,"MELON":80}
_ANIMAL_COST={"GOOSE":300,"COW":400,"SHEEP":500}
_PRODUCTS=("WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER")
_STATE={0:{},1:{}}


def _g(value,key,default=None):
    if isinstance(value,dict):return value.get(key,default)
    getter=getattr(value,"get",None)
    return getter(key,default) if callable(getter) else getattr(value,key,default)


def _seat(obs):return 1 if int(_g(obs,"player",0) or 0)==1 else 0
def _step(obs):return min(718,max(0,int(_g(obs,"step",0) or 0)))
def _farm(obs):return list(_g(obs,"farms",[]) or [])[_seat(obs)]
def _positions(obs):
    farm=_farm(obs)
    return [tuple(map(int,_g(farm,"farmer",[4,4]))),*[tuple(map(int,value)) for value in list(_g(farm,"hands",[]) or [])]]
def _inventories(obs,count):
    values=[dict(value or {}) for value in list(_g(_g(obs,"private",{}) or {},"inventories",[]) or [])]
    values.extend({} for _ in range(max(0,count-len(values))))
    return values[:count]
def _tile(obs,position):
    try:
        x,y=position;rows=list(_g(_farm(obs),"tiles",[]) or [])
        return rows[y][x] if 0<=y<len(rows) and 0<=x<len(rows[y]) else "LOCKED"
    except Exception:return "LOCKED"
def _copy(action):
    action=copy.deepcopy(action or {})
    return {"farmer":list(action.get("farmer") or ["PASS"]),"hands":[list(x or ["PASS"]) for x in action.get("hands",[])],"market":[list(x) for x in action.get("market",[]) if x]}
def _align(action,obs):
    action=_copy(action);n=len(list(_g(_farm(obs),"hands",[]) or []));action["hands"].extend([["PASS"] for _ in range(max(0,n-len(action["hands"]))) ]);action["hands"]=action["hands"][:n];action["market"]=action["market"][:10];return action
def _toward(source,target):
    sx,sy=source;tx,ty=target
    if sx<tx:return ["EAST"]
    if sx>tx:return ["WEST"]
    if sy<ty:return ["SOUTH"]
    if sy>ty:return ["NORTH"]
    return ["PASS"]
def _nearest_access(position):return min(_ACCESS,key=lambda p:abs(position[0]-p[0])+abs(position[1]-p[1]))
def _record(st,name):st["experts"][name]=int(st["experts"].get(name,0))+1


def _valid(obs,actor,order):
    if not order or order[0]=="PASS":return True
    positions=_positions(obs)
    if actor>=len(positions):return False
    pos=positions[actor];tile=_tile(obs,pos);inv=_inventories(obs,len(positions))[actor];private=_g(obs,"private",{}) or {};shed=dict(_g(private,"shed",{}) or {});seeds=dict(_g(private,"seeds",{}) or {});op=str(order[0])
    if op in _MOVES:
        dx,dy=_MOVES[op];rows=list(_g(_farm(obs),"tiles",[]) or []);x,y=pos[0]+dx,pos[1]+dy;return 0<=y<len(rows) and 0<=x<len(rows[y])
    if op=="DIG":return tile!="LOCKED" and not(isinstance(tile,dict) and tile.get("animal"))
    if op=="PLANT":return tile is None and len(order)>1 and int(seeds.get(order[1],0) or 0)>0
    if op=="WATER":return isinstance(tile,dict) and tile.get("kind")=="PLANT" and not tile.get("watered_today")
    if op=="HARVEST":return isinstance(tile,dict) and int(tile.get("yield_units",0) or 0)>0
    if op=="FERTILIZE":return isinstance(tile,dict) and tile.get("kind")=="PLANT" and int(inv.get("FERTILIZER",0) or 0)>0
    if op in {"BUILD_COOP","BUILD_PASTURE"}:return tile is None
    if op=="FEED":return isinstance(tile,dict) and bool(tile.get("animal")) and not tile.get("fed_today") and int(inv.get("WHEAT",0) or 0)>0
    if op=="CARE":return isinstance(tile,dict) and bool(tile.get("animal")) and not tile.get("cared_today")
    if op=="COLLECT_FERTILIZER":return isinstance(tile,dict) and bool(tile.get("fertilizer_available"))
    if op=="PICKUP":return pos in _ACCESS and len(order)>2 and int(shed.get(order[1],0) or 0)>0
    if op=="DROP":return pos in _ACCESS and sum(max(0,int(v or 0)) for v in inv.values())>0
    if op=="PLACE":return len(order)>1 and int(inv.get(order[1],0) or 0)>0
    return False


def _growth_executor(obs,action,st):
    action=_align(action,obs);positions=_positions(obs);targets=[tuple(x) for x in _TARGETS[_step(obs)].get("positions",[])];orders=[action["farmer"],*action["hands"]];expert="growth_continuation"
    for actor,order in enumerate(list(orders)):
        if _valid(obs,actor,order):continue
        pos=positions[actor];tile=_tile(obs,pos);replacement=None;op=str(order[0]) if order else "PASS"
        if op in {"PLANT","BUILD_COOP","BUILD_PASTURE"} and isinstance(tile,dict) and tile.get("kind")=="WEED":replacement=["DIG"];expert="state_recovery"
        elif op in {"PICKUP","DROP"} and pos not in _ACCESS:replacement=_toward(pos,_nearest_access(pos));expert="inventory_recovery"
        elif actor<len(targets) and pos!=targets[actor]:replacement=_toward(pos,targets[actor]);expert="state_recovery"
        orders[actor]=replacement or ["PASS"];st["divergence"]+=1
    action["farmer"],action["hands"]=orders[0],orders[1:];_record(st,expert);return action


def _projected_shed(obs,action):
    projected={k:max(0,int(v or 0)) for k,v in dict(_g(_g(obs,"private",{}) or {},"shed",{}) or {}).items()};positions=_positions(obs);inventories=_inventories(obs,len(positions));orders=[action["farmer"],*action["hands"]]
    for actor,order in enumerate(orders):
        if actor>=len(positions) or positions[actor] not in _ACCESS:continue
        deposits=list(inventories[actor].items()) if order and order[0]=="DROP" else [(str(order[1]),int(order[2] or 1) if len(order)>2 else 1)] if order and order[0]=="PLACE" and len(order)>1 else []
        for item,requested in deposits:
            room=max(0,100-sum(projected.values()));amount=min(max(0,int(requested or 0)),max(0,int(inventories[actor].get(item,0) or 0)),room);projected[item]=projected.get(item,0)+amount
    return projected


def _safe_market(obs,action,st,liquidate=False):
    projected=_projected_shed(obs,action);market=[] if liquidate else [list(x) for x in action["market"]];available=dict(projected)
    if liquidate:
        market=[["SELL",item,available[item]] for item in _PRODUCTS if available.get(item,0)>0][:_10()];_record(st,"capital_preservation")
    else:
        for order in market:
            if len(order)>=3 and order[0]=="SELL":item=str(order[1]);q=min(max(0,int(order[2] or 0)),available.get(item,0));order[2]=q;available[item]=max(0,available.get(item,0)-q)
        if _step(obs)>=715:
            planned={str(x[1]):max(0,int(x[2] or 0)) for x in market if len(x)>=3 and x[0]=="SELL"}
            for item in _PRODUCTS:
                extra=max(0,projected.get(item,0)-planned.get(item,0))
                if extra and len(market)<10:market.append(["SELL",item,extra]);_record(st,"terminal_liquidation")
    action["market"]=market[:10];return action
def _10():return 10


def _risk_option(obs,st):
    positions=_positions(obs);inventories=_inventories(obs,len(positions));orders=[]
    for pos,inventory in zip(positions,inventories):
        carried=sum(max(0,int(v or 0)) for v in inventory.values())
        orders.append(["DROP"] if carried and pos in _ACCESS else _toward(pos,_nearest_access(pos)) if carried else ["PASS"])
    action={"farmer":orders[0],"hands":orders[1:],"market":[]};_record(st,"logistics_recovery");return _safe_market(obs,action,st,True)


def _reset(obs):
    seat,step=_seat(obs),_step(obs);st=_STATE[seat]
    if step==0 or step<int(st.get("last",-1)):st.clear();st.update(last=step,calls=0,experts={},fallback=0,changed_calls=0,divergence=0,risk=False)
    st["last"]=step;st["calls"]=int(st.get("calls",0))+1
    if _FULL and step==576:
        farms=list(_g(obs,"farms",[]) or []);gap=int(_g(farms[seat],"money",0) or 0)-int(_g(farms[1-seat],"money",0) or 0);st["risk"]=gap<=-5129
    return st
def _fallback(obs):return {"farmer":["PASS"],"hands":[["PASS"] for _ in list(_g(_farm(obs),"hands",[]) or [])],"market":[]}
def model_status():return {"kind":"v106_conformal_support_option_moe","model_id":"v106_conformal_support_option_moe","strategy_parent":None,"strength_comparator":"v76_adjacent_safe_buy_lead","mode":"full" if _FULL else "ablation","router":"grouped-oof-public-tail-risk-tree","experts":["growth_continuation","state_recovery","inventory_recovery","logistics_recovery","capital_preservation","terminal_liquidation"],"stats":copy.deepcopy(_STATE)}
def agent(obs,configuration=None):
    del configuration
    try:
        st=_reset(obs);raw=_align(_ACTIONS[_step(obs)],obs)
        if not _FULL:_record(st,"growth_continuation");return raw
        if st.get("risk"):
            action=_risk_option(obs,st)
        elif _step(obs)>=576:
            action=_safe_market(obs,_growth_executor(obs,raw,st),st,False)
        else:
            action=raw;_record(st,"growth_continuation")
        st["changed_calls"]+=int(action!=raw);return _align(action,obs)
    except Exception:
        st=_STATE[_seat(obs)];st["fallback"]=int(st.get("fallback",0))+1;return _fallback(obs)
