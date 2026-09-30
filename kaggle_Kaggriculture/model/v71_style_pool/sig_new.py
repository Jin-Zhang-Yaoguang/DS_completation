"""新方案在 r25 视角下的 rkey 与 t92/t58 现金跳变。用法: python sig_new.py opp,opp"""
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
def one(o):
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP[o]).parent))
    import fidelity, engine
    me=fidelity.make_agent(f"sub:{HERE}/agents/v54r34_main.py"); op=fidelity.make_agent(f"sub:{OPP[o]}")
    k=engine.load_kagsim(); g=k.Game(seed=18001); m=[]
    for t in range(100):
        obs=[g.observe(0),g.observe(1)]; m.append(float(obs[0]["farms"][1]["money"]))
        if t==2: rk=(m[-1],int(obs[0]["market"]["inventory"]["WHEAT"]))
        g.step(me(obs[0]),op(obs[1]))
    return o,rk,m[92]-m[91],m[58]-m[57]
if __name__=="__main__":
    with ProcessPoolExecutor(4) as ex:
        for o,rk,d92,d58 in ex.map(one,sys.argv[1].split(",")): print(f"{o:14s} rkey {rk}  t92跳变 {d92:+.0f}  t58跳变 {d58:+.0f}")
