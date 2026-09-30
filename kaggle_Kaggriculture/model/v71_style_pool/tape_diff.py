"""比对各公开代理的带库内容:哪些带是 rescue7 带库没有的。"""
import sys, json, hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
import fidelity
def routes_of(name):
    ag=fidelity.make_agent(f"sub:{HERE}/agents/{name}_main.py")
    try: ag({"step":0,"player":0})
    except Exception: pass
    impl=None
    for attr in dir(ag):
        v=getattr(ag,attr,None)
        if hasattr(v,"chassis"): impl=v; break
    if impl is None:
        g=getattr(ag,"__globals__",{}) or {}
        impl=g.get("_IMPL")
    if impl is None: return None
    out={}
    for rid,tape in impl.chassis.routes.items():
        h=hashlib.md5(json.dumps(tape,sort_keys=True,default=str).encode()).hexdigest()[:10]
        out[rid]=h
    return out
base=routes_of("rescue7")
print(f"rescue7 带库: {len(base)} 条")
baseset=set(base.values())
for name in ("metav4","guru_v4","multiroute","hai2965","evgen","v56","v54"):
    try:
        r=routes_of(name)
        if r is None: print(f"{name:12s} 无法读取"); continue
        new=[(rid,h) for rid,h in r.items() if h not in baseset]
        same=len(r)-len(new)
        print(f"{name:12s} {len(r):3d} 条 | 与 rescue7 相同 {same:3d} | **新带 {len(new):3d}** {[rid for rid,_ in new][:12]}")
    except Exception as e:
        print(f"{name:12s} ERR {type(e).__name__}: {e}")
