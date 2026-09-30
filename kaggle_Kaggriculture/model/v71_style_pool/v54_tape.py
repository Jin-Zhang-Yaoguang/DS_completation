"""V54 原版在 wk5live 196 局真实对手动作带上的重放(与 y68wk5 当时的真实成绩对比)。"""
import sys, json, glob, collections, statistics as st
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
def one(fn):
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    r = json.load(open(fn)); nm = r["info"]["TeamNames"]; s = r["steps"]
    if nm.count("datatuu") != 1: return None
    seat = nm.index("datatuu"); o = 1 - seat
    a1 = [x for x in (s[1][o].get("action") or {}).get("market") or [] if x]
    buy1 = sum(int(x[2]) for x in a1 if x[0] == "BUY_PRODUCT" and len(x) > 2)
    sell1 = sum(int(x[2]) for x in a1 if x[0] == "SELL" and len(x) > 2)
    op = fidelity.tape_agent([s[t+1][o].get("action") or {} for t in range(len(s)-1)])
    me = fidelity.make_agent(f"sub:{HERE}/agents/v54_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=r["info"]["seed"])
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = me(obs[seat]); a[o] = op(obs[o]); g.step(a[0], a[1])
    return nm[o], f"买{buy1}卖{sell1}", float(g.reward(seat)-g.reward(o)), float(r["rewards"][seat]-r["rewards"][o])
if __name__ == "__main__":
    fs = sorted(glob.glob(str(HERE/"wk5live"/"episode-*.json")))
    with ProcessPoolExecutor(7) as ex: res = [x for x in ex.map(one, fs, chunksize=2) if x]
    w = sum(1 for x in res if x[2] > 0); wl = sum(1 for x in res if x[3] > 0)
    print(f"{len(res)} 局: V54 重放 {w} 胜 ({w/len(res):.0%}) | y68wk5 线上实际 {wl} 胜 ({wl/len(res):.0%})")
    byf = collections.defaultdict(lambda: [0, 0, 0])
    for opp, f2, m, live in res:
        x = byf[f2]; x[0] += m > 0; x[1] += live > 0; x[2] += 1
    for f2, x in sorted(byf.items(), key=lambda kv: -kv[1][2])[:10]:
        print(f"  {f2:10s} {x[2]:3d} 局  V54 {x[0]:3d} 胜 | wk5 {x[1]:3d} 胜")
    loss = sorted([x for x in res if x[2] <= 0], key=lambda z: z[2])[:8]
    print("V54 最大输局:", [(x[0][:12], x[1], round(x[2])) for x in loss])
