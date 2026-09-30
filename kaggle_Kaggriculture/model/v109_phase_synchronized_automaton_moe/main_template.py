"""Standalone phase-synchronized finite-state Hierarchical MoE."""
import base64,copy,json,zlib
__version__="v109-phase-synchronized-automaton-moe-rc1";_FULL="__MODE__"=="full";_D=json.loads(zlib.decompress(base64.b85decode("__PAYLOAD__")).decode());_A=_D["actions"];_T=_D["targets"]
_MOVES={"NORTH":(0,-1),"SOUTH":(0,1),"EAST":(1,0),"WEST":(-1,0)};_ACCESS={(4,4),(5,4),(4,5),(5,5)};_STATE={0:{},1:{}}
def _g(v,k,d=None):
    if isinstance(v,dict):return v.get(k,d)
    f=getattr(v,"get",None);return f(k,d) if callable(f) else getattr(v,k,d)
def _seat(o):return 1 if int(_g(o,"player",0) or 0)==1 else 0
def _step(o):return min(718,max(0,int(_g(o,"step",0) or 0)))
def _farm(o):return list(_g(o,"farms",[]) or [])[_seat(o)]
def _positions(o):
    f=_farm(o);return [tuple(map(int,_g(f,"farmer",[4,4]))),*[tuple(map(int,x)) for x in list(_g(f,"hands",[]) or [])]]
def _inventories(o,n):
    xs=[dict(x or {}) for x in list(_g(_g(o,"private",{}) or {},"inventories",[]) or [])];xs.extend({} for _ in range(max(0,n-len(xs))));return xs[:n]
def _tile(o,p):
    try:
        x,y=p;rows=list(_g(_farm(o),"tiles",[]) or []);return rows[y][x] if 0<=y<len(rows) and 0<=x<len(rows[y]) else "LOCKED"
    except Exception:return "LOCKED"
def _copy(a):
    a=copy.deepcopy(a or {});return {"farmer":list(a.get("farmer") or ["PASS"]),"hands":[list(x or ["PASS"]) for x in a.get("hands",[])],"market":[list(x) for x in a.get("market",[]) if x]}
def _align(a,o):
    a=_copy(a);n=len(list(_g(_farm(o),"hands",[]) or []));a["hands"].extend([["PASS"] for _ in range(max(0,n-len(a["hands"]))) ]);a["hands"]=a["hands"][:n];a["market"]=a["market"][:10];return a
def _summary(o):
    s=_seat(o);farms=list(_g(o,"farms",[]) or []);f=farms[s];r=farms[1-s];private=_g(o,"private",{}) or {};return {"positions":_positions(o),"money":int(_g(f,"money",0) or 0),"rival_money":int(_g(r,"money",0) or 0),"hands":len(list(_g(f,"hands",[]) or [])),"quadrants":len(list(_g(f,"unlocked_quadrants",[]) or [])),"seeds":{k:int(v or 0) for k,v in dict(_g(private,"seeds",{}) or {}).items()},"shed":{k:int(v or 0) for k,v in dict(_g(private,"shed",{}) or {}).items()}}
def _dist(x,t):
    tp=[tuple(p) for p in t.get("positions",[])];pos=sum(abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(x["positions"],tp))+5*abs(len(x["positions"])-len(tp));asset=8*abs(x["hands"]-t["hands"])+12*abs(x["quadrants"]-t["quadrants"]);cash=abs(x["money"]-t["money"])/1000+abs((x["money"]-x["rival_money"])-(t["money"]-t["rival_money"]))/2000;stock=sum(abs(x["seeds"].get(k,0)-t["seeds"].get(k,0)) for k in set(x["seeds"])|set(t["seeds"]))/8+sum(abs(x["shed"].get(k,0)-t["shed"].get(k,0)) for k in set(x["shed"])|set(t["shed"]))/12;return pos+asset+cash+stock
def _valid(o,i,a):
    if not a or a[0]=="PASS":return True
    ps=_positions(o)
    if i>=len(ps):return False
    p=ps[i];tile=_tile(o,p);inv=_inventories(o,len(ps))[i];private=_g(o,"private",{}) or {};shed=dict(_g(private,"shed",{}) or {});seeds=dict(_g(private,"seeds",{}) or {});op=str(a[0])
    if op in _MOVES:
        dx,dy=_MOVES[op];rows=list(_g(_farm(o),"tiles",[]) or []);x,y=p[0]+dx,p[1]+dy;return 0<=y<len(rows) and 0<=x<len(rows[y])
    if op=="DIG":return tile!="LOCKED" and not(isinstance(tile,dict) and tile.get("animal"))
    if op=="PLANT":return tile is None and len(a)>1 and int(seeds.get(a[1],0) or 0)>0
    if op=="WATER":return isinstance(tile,dict) and tile.get("kind")=="PLANT" and not tile.get("watered_today")
    if op=="HARVEST":return isinstance(tile,dict) and int(tile.get("yield_units",0) or 0)>0
    if op=="FERTILIZE":return isinstance(tile,dict) and tile.get("kind")=="PLANT" and int(inv.get("FERTILIZER",0) or 0)>0
    if op in {"BUILD_COOP","BUILD_PASTURE"}:return tile is None
    if op=="FEED":return isinstance(tile,dict) and bool(tile.get("animal")) and int(inv.get("WHEAT",0) or 0)>0
    if op=="CARE":return isinstance(tile,dict) and bool(tile.get("animal"))
    if op=="COLLECT_FERTILIZER":return isinstance(tile,dict) and bool(tile.get("fertilizer_available"))
    if op=="PICKUP":return p in _ACCESS and len(a)>2 and int(shed.get(a[1],0) or 0)>0
    if op=="DROP":return p in _ACCESS and sum(max(0,int(v or 0)) for v in inv.values())>0
    if op=="PLACE":return len(a)>1 and int(inv.get(a[1],0) or 0)>0
    return False
def _projected_shed(o,a):
    projected={k:max(0,int(v or 0)) for k,v in dict(_g(_g(o,"private",{}) or {},"shed",{}) or {}).items()};positions=_positions(o);inventories=_inventories(o,len(positions));orders=[a["farmer"],*a["hands"]]
    for actor,order in enumerate(orders):
        if actor>=len(positions) or positions[actor] not in _ACCESS:continue
        deposits=list(inventories[actor].items()) if order and order[0]=="DROP" else [(str(order[1]),int(order[2] or 1) if len(order)>2 else 1)] if order and order[0]=="PLACE" and len(order)>1 else []
        for item,requested in deposits:
            room=max(0,100-sum(projected.values()));amount=min(max(0,int(requested or 0)),max(0,int(inventories[actor].get(item,0) or 0)),room);projected[item]=projected.get(item,0)+amount
    return projected
def _safe(a,o,st):
    a=_align(a,o);units=[a["farmer"],*a["hands"]]
    for i,x in enumerate(units):
        if not _valid(o,i,x):units[i]=["PASS"];st["dropped"]+=1
    a["farmer"],a["hands"]=units[0],units[1:];available=_projected_shed(o,a)
    for order in a["market"]:
        if len(order)>=3 and order[0]=="SELL":item=str(order[1]);q=min(max(0,int(order[2] or 0)),available.get(item,0));order[2]=q;available[item]=max(0,available.get(item,0)-q)
    return a
def _reset(o):
    s,step=_seat(o),_step(o);st=_STATE[s]
    if step==0 or step<int(st.get("last",-1)):st.clear();st.update(last=step,calls=0,phase=-1,experts={},fallback=0,changed_calls=0,dropped=0)
    st["last"]=step;st["calls"]+=1;return st
def _rec(st,e):st["experts"][e]=int(st["experts"].get(e,0))+1
def _fallback(o):return {"farmer":["PASS"],"hands":[["PASS"] for _ in list(_g(_farm(o),"hands",[]) or [])],"market":[]}
def model_status():return {"kind":"v109_phase_synchronized_automaton_moe","model_id":"v109_phase_synchronized_automaton_moe","strategy_parent":None,"strength_comparator":"v76_adjacent_safe_buy_lead","mode":"full" if _FULL else "ablation","router":"monotone-latent-production-phase-router","experts":["hold_option","nominal_option","catch_up_option"],"stats":copy.deepcopy(_STATE)}
def agent(obs,configuration=None):
    del configuration
    try:
        st=_reset(obs);step=_step(obs);phase=step
        if _FULL:
            lo=max(0,int(st["phase"]),step-2);hi=min(718,max(lo,int(st["phase"])+2),step+2);state=_summary(obs);phase=min(range(lo,hi+1),key=lambda p:(_dist(state,_T[p]),abs(p-step),p));st["phase"]=phase
        expert="hold_option" if phase<step else "catch_up_option" if phase>step else "nominal_option";_rec(st,expert);action=_safe(_A[phase],obs,st);st["changed_calls"]+=int(phase!=step);return action
    except Exception:
        st=_STATE[_seat(obs)];st["fallback"]=int(st.get("fallback",0))+1;return _fallback(obs)
