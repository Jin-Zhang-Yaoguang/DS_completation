import sys, tarfile, io, ast, time
from pathlib import Path
DB=sys.argv[1]; src=open("agents/v54r30_main.py","rb").read(); compile(src,"main.py","exec")
last=[n.name for n in ast.parse(src).body if isinstance(n,ast.FunctionDef)][-1]
with tarfile.open(f"{DB}/submission_v54r30.tar.gz","w:gz") as tf:
    ti=tarfile.TarInfo("main.py"); ti.size=len(src); ti.mtime=1_700_000_000; tf.addfile(ti,io.BytesIO(src))
with tarfile.open(f"{DB}/submission_v54r30.tar.gz") as tf: ok=tf.getnames()==["main.py"] and tf.extractfile("main.py").read()==src
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
import fidelity, engine
from pub_splice import OPP
sys.path.insert(0,str(Path(OPP["engineV3"]).parent))
me=fidelity.make_agent("sub:agents/v54r30_main.py"); op=fidelity.make_agent(f"sub:{OPP['engineV3']}")
k=engine.load_kagsim(); g=k.Game(seed=18101); ts=[]
while not engine._val(g.done):
    obs=[g.observe(0),g.observe(1)]; t0=time.perf_counter(); a=me(obs[0]); ts.append(time.perf_counter()-t0); g.step(a,op(obs[1]))
print("入口",last,"包校验",ok,f"单步最大 {max(ts):.3f}s")
