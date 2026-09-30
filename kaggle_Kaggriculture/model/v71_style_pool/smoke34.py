import sys, time
from pathlib import Path
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
import fidelity, engine
ns={}; exec(Path(f"agents/{sys.argv[1]}_main.py").read_text(), ns)
me=[v for k,v in ns.items() if callable(v) and not k.startswith("__")][-1]; print("入口",me.__name__)
sys.path.insert(0,"agents"); op=fidelity.make_agent("sub:agents/me2965_28_main.py")
k=engine.load_kagsim(); g=k.Game(seed=int(sys.argv[2]) if len(sys.argv)>2 else 18001); ts=[]
while not engine._val(g.done):
    obs=[g.observe(0),g.observe(1)]; t0=time.perf_counter(); a=me(obs[0]); ts.append(time.perf_counter()-t0); g.step(a,op(obs[1]))
print("差",float(g.reward(0)-g.reward(1)),f"单步最大 {max(ts):.3f}s 总 {sum(ts):.1f}s")
err=0; ch=0
for n,v in ns.items():
    if n.endswith("_REPORT") and isinstance(v,dict) and (n.startswith("_S") or n in ("_HR_REPORT",)):
        err+=int(v.get("errors",0) or 0); ch+=int(v.get("changed",0) or 0)
print("尾部层 errors 合计",err,"changed 合计",ch, "HP",ns.get("_HP_STATS"))
