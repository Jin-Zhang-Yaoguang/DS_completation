# 复刻:DeeperNet 的固定带(按商店查表)。仅作本地对手代表。
import json as _json, copy as _copy
_D=_json.load(open("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v71_style_pool/agents/afrep_deepernet.json"))
_ST={}
def _pick(shops):
    s=list(shops or [])
    if len(s)>=2 and "|".join(s[:2]) in _D["by_shops"]: return _D["by_shops"]["|".join(s[:2])]["tape"]
    if len(s)>=1 and s[0] in _D["first_shop"]: return _D["first_shop"][s[0]]["tape"]
    return _D["default"]["tape"]
def afrep_deepernet_agent(observation, configuration=None):
    step=int(observation.get("step",0)); p=int(observation.get("player",0))
    st=_ST.get(p)
    if st is None or step==0 or step<=st["last"]: st={"last":-1,"tape":_D["default"]["tape"]}; _ST[p]=st
    st["last"]=step
    if step in (72,144):
        st["tape"]=_pick(((observation.get("town") or {}).get("unlocked_shops")))
    t=st["tape"]
    return _copy.deepcopy(t[step]) if step<len(t) else {"farmer":["PASS"],"hands":[],"market":[]}
