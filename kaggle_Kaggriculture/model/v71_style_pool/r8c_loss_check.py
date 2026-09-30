"""r8c 对败局 tape 验证 + 对 rescue7 该组合不受扰动。"""
import sys, os, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
import fidelity, engine
os.environ.pop("KAG_FORCE_ROUTE",None); os.environ.pop("KAG_FORCE_ROUTE2",None)
r=json.load(open(HERE/"rlive"/"episode-111981662-replay.json")); s=r["steps"]
nm=r["info"]["TeamNames"]; seat=nm.index("datatuu"); o=1-seat
for ver in ("v54r8b","v54r8c"):
    op=fidelity.tape_agent([s[t+1][o].get("action") or {} for t in range(len(s)-1)])
    me=fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py")
    k=engine.load_kagsim(); g=k.Game(seed=r["info"]["seed"])
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
    print(f"{ver} 败局重放: {g.reward(seat)-g.reward(o):+.0f}")
