"""本地所有候选代理的 rkey(我方 r38 视角 t2 观测对手现金, 市场小麦库存)。"""
import sys, json, glob, os
from pathlib import Path
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
import fidelity, engine
from pub_splice import OPP
paths=dict(OPP)
for f in glob.glob(str(M/"**/*main*.py"),recursive=True)+glob.glob(str(M/"**/agents/*.py"),recursive=True):
    paths.setdefault(f,f)
out={}
for name,p in sorted(paths.items()):
    if not os.path.exists(p) or os.path.getsize(p)<2000: continue
    try:
        sys.path.insert(0,str(Path(p).parent))
        a=fidelity.make_agent(f"sub:{p}"); k=engine.load_kagsim(); g=k.Game(seed=1500000017); ob=None
        for t in range(3):
            o0=g.observe(0); o1=g.observe(1); g.step(None if t<0 else a(o0), None)
        ob=g.observe(1); rk=(round(ob["farms"][0]["money"]),ob["market"]["inventory"]["WHEAT"])
        out[name]=rk
    except Exception as e: out[name]=str(e)[:40]
    finally: sys.path.pop(0)
json.dump(out,open("rkey_local.json","w"),ensure_ascii=False)
for n,v in out.items():
    if isinstance(v,tuple) and v[0]<900: print("低现金:",n,v)
print("共",len(out))
