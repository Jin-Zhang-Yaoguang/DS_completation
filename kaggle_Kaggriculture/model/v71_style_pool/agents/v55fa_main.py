# v55f:v55d + 路线前缀树(轴0):第 k 家商店解锁时(t=72k,k>=3),在 Arjun 全量库中找「前 k 家商店与本局相同、且最近 WIN 步动作与我方已执行动作一致」的对局,切到它的后续带。
import json as _json, copy as _copy, os as _os
_H="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v71_style_pool/agents/"
_D=_json.load(open(_H+"afrep_arjun.json"))
_OVR=_json.load(open(_H+"v55d_ovr.json"))
_LIB=_json.load(open(_H+"arjun100.json"))
_PASS={"farmer":["PASS"],"hands":[],"market":[]}
_ST={}
_LEADN=8
_LEAD_ITEMS=("CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER")
_WIN=int(_os.environ.get("KAG_TREE_WIN","72")); _TOL=int(_os.environ.get("KAG_TREE_TOL","8"))
_TSTEPS=tuple(int(x) for x in _os.environ.get("KAG_TREE_STEPS","216,288,360,432,504,576").split(",") if x)
def _k(a): return _json.dumps(a or _PASS,sort_keys=True)
_LK={e:[_k(a) for a in v["tape"]] for e,v in _LIB.items()}
def _pick(shops):
    s=list(shops or [])
    if len(s)>=2 and "|".join(s[:2]) in _OVR: return _OVR["|".join(s[:2])]
    if len(s)>=2 and "|".join(s[:2]) in _D["by_shops"]: return _D["by_shops"]["|".join(s[:2])]["tape"]
    if len(s)>=1 and s[0] in _D["first_shop"]: return _D["first_shop"][s[0]]["tape"]
    return _D["default"]["tape"]
def _tree(st,shops,step):
    k=step//72; s=list(shops or [])
    if len(s)<k: return
    best=None
    for e,v in _LIB.items():
        if v["shops"][:k]!=s[:k]: continue
        L=_LK[e]; mis=sum(1 for t in range(max(0,step-_WIN),step) if t>=len(L) or L[t]!=st["exec"][t])
        if mis>_TOL: continue
        cur=st["tape"] is v["tape"]
        key=(mis,not cur,not v["won"],-v["margin"])
        if best is None or key<best[0]: best=(key,e)
    if best: st["tape"]=_LIB[best[1]]["tape"]; st["eid"]=best[1]
def _planned(tape,item,a,b):
    q=0
    for t in range(max(0,a),min(len(tape),b)):
        for o in ((tape[t] or {}).get("market") or []):
            if o and o[0]=="SELL" and len(o)>=3 and o[1]==item:
                try: q+=int(o[2])
                except Exception: pass
    return q
def v55fa_agent(observation, configuration=None):
    step=int(observation.get("step",0)); p=int(observation.get("player",0))
    st=_ST.get(p)
    if st is None or step==0 or step<=st["last"]:
        st={"last":-1,"tape":_D["default"]["tape"],"debt":{},"exec":[],"eid":None}; _ST[p]=st
    st["last"]=step
    shops=((observation.get("town") or {}).get("unlocked_shops"))
    if step in (72,144):
        st["tape"]=_pick(shops)
    elif step in _TSTEPS:
        try: _tree(st,shops,step)
        except Exception: pass
    tape=st["tape"]
    raw=tape[step] if step<len(tape) and tape[step] else _PASS
    while len(st["exec"])<step: st["exec"].append(_k(_PASS))
    st["exec"].append(_k(raw))
    action=_copy.deepcopy(raw)
    try:
        if _LEADN>0 and step<700:
            market=action.setdefault("market",[]); debt=st["debt"]
            for o in market:
                if o and o[0]=="SELL" and len(o)>=3 and debt.get(o[1],0)>0:
                    cut=min(int(o[2]),debt[o[1]]); o[2]=int(o[2])-cut; debt[o[1]]-=cut
            market[:]=[o for o in market if not (o and o[0]=="SELL" and len(o)>=3 and int(o[2])<=0)]
            shed=((observation.get("private") or {}).get("shed") or {}); prices=((observation.get("market") or {}).get("prices") or {})
            for item in _LEAD_ITEMS:
                queued=sum(int(o[2]) for o in market if o and o[0]=="SELL" and len(o)>=3 and o[1]==item)
                avail=int(shed.get(item,0))-queued
                planned=_planned(tape,item,step+1,step+1+_LEADN)-debt.get(item,0)
                q=min(avail,planned)
                if q<=0 or prices.get(item,0)<2: continue
                for o in market:
                    if o and o[0]=="SELL" and len(o)>=3 and o[1]==item: o[2]=int(o[2])+q; break
                else:
                    if len(market)>=10: continue
                    market.append(["SELL",item,q])
                debt[item]=debt.get(item,0)+q
    except Exception:
        pass
    return action
