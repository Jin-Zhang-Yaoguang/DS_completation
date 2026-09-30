import sys, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
import fidelity, engine
ver=sys.argv[1]; ns={}; exec((HERE/f"agents/{ver}_main.py").read_text(), ns)
fns=[v for k,v in ns.items() if callable(v) and not k.startswith("__")]; me=fns[-1]; print("入口",fns[-1].__name__)
op=fidelity.make_agent(f"sub:{HERE}/agents/rescue7_main.py")
k=engine.load_kagsim(); g=k.Game(seed=18001)
while not engine._val(g.done):
    obs=[g.observe(0),g.observe(1)]; g.step(me(obs[0]),op(obs[1]))
print("差",float(g.reward(0)-g.reward(1)))
for n in ("_R148_REPORT","_ADV_REPORT","_VQ_REPORT","_FRO_REPORT","_T62A_REPORT","_DSM_REPORT","_R25_FEAS_REPORT","_FX_REPORT","_DP_REPORT","_BD_REPORT","_MPX_REPORT","_SM_REPORT","_CXD_REPORT","_E410_REPORT","_E402_REPORT","_MG_REPORT","_IG_REPORT"):
    if n in ns: print(n, ns[n])
