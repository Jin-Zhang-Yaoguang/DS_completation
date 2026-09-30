"""单局动作带复现:python one_tape.py <rlive3 eid> <agent> [env=val ...]"""
import sys, os, json, collections
from pathlib import Path
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
for kv in sys.argv[3:]: k,v=kv.split("=",1); os.environ[k]=v
sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
import fidelity, engine
r=json.load(open(f"rlive3/{sys.argv[1]}.json")); seat=r["seat"]; o=1-seat
ns={}; exec(Path(f"agents/{sys.argv[2]}_main.py").read_text(), ns); me=[v for k,v in ns.items() if callable(v) and not k.startswith("__")][-1]
op=fidelity.tape_agent([r["acts"][t+1][o] for t in range(len(r["acts"])-1)])
k=engine.load_kagsim(); g=k.Game(seed=r["seed"]); buys=[]; t=0
while not engine._val(g.done):
    obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o])
    buys+=[(t,x[1]) for x in (a[seat].get("market") or []) if x and x[0]=="BUY_ANIMAL"]
    g.step(a[0],a[1]); t+=1
print(sys.argv[2:], "差",float(g.reward(seat)-g.reward(o)),"买畜",buys, ns.get("_DSM_REPORT"))
