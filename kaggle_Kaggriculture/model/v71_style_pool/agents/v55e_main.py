# v55e:按对手类型条件替换 —— 对手第2步现金<900(动物优先开局)时用原 v55b 分支,否则用 v55d 的 15 个替换分支。原注释:v55b + 15 个商店组合换成验证过的更好 Arjun 分支(v55_cellsel)。原注释:底盘 = Arjun 动物流固定带(按商店查表的纯动作带复刻);部件:提前 N 步卖出(含肥料)。
import json as _json, copy as _copy
_D=_json.load(open("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v71_style_pool/agents/afrep_arjun.json"))
_PASS={"farmer":["PASS"],"hands":[],"market":[]}
_ST={}
_LEADN=8
_LEAD_ITEMS=("CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER")
_OVR=_json.load(open("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v71_style_pool/agents/v55d_ovr.json"))
def _pick(shops,kind=None):
    s=list(shops or [])
    if kind!="af" and len(s)>=2 and "|".join(s[:2]) in _OVR: return _OVR["|".join(s[:2])]
    if len(s)>=2 and "|".join(s[:2]) in _D["by_shops"]: return _D["by_shops"]["|".join(s[:2])]["tape"]
    if len(s)>=1 and s[0] in _D["first_shop"]: return _D["first_shop"][s[0]]["tape"]
    return _D["default"]["tape"]
def _planned(tape,item,a,b):
    q=0
    for t in range(max(0,a),min(len(tape),b)):
        for o in ((tape[t] or {}).get("market") or []):
            if o and o[0]=="SELL" and len(o)>=3 and o[1]==item:
                try: q+=int(o[2])
                except Exception: pass
    return q
def v55e_agent(observation, configuration=None):
    step=int(observation.get("step",0)); p=int(observation.get("player",0))
    st=_ST.get(p)
    if st is None or step==0 or step<=st["last"]:
        st={"last":-1,"tape":_D["default"]["tape"],"debt":{}}; _ST[p]=st
    st["last"]=step
    if step==2:
        try: st["kind"]="af" if float(observation["farms"][1-p]["money"])<900 else None
        except Exception: st["kind"]=None
    if step in (72,144):
        st["tape"]=_pick(((observation.get("town") or {}).get("unlocked_shops")),st.get("kind"))
    tape=st["tape"]
    action=_copy.deepcopy(tape[step]) if step<len(tape) and tape[step] else _copy.deepcopy(_PASS)
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
