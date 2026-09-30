"""专项:y68wk2 线上 replay 全量动作带重放 y68wk2 vs y68wk5,按对手开局族分组。"""
import sys, json, glob, collections, statistics as st
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
S = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
def fam(rep, o):
    a1 = [x for x in (rep["steps"][1][o].get("action") or {}).get("market") or [] if x]
    a2 = [x for x in (rep["steps"][2][o].get("action") or {}).get("market") or [] if x]
    buy1 = sum(int(x[2]) for x in a1 if x[0] == "BUY_PRODUCT" and len(x) > 2)
    sell1 = sum(int(x[2]) for x in a1 if x[0] == "SELL" and len(x) > 2)
    buy2 = sum(int(x[2]) for x in a2 if x[0] == "BUY_PRODUCT" and len(x) > 2)
    hire2 = sum(1 for x in a2 if x[0] == "HIRE")
    if buy1 == 7 and sell1 == 2: return "买7卖2挤压"
    if buy1 <= 7 and sell1 <= 2 and (hire2 >= 4 or buy2 >= 20): return "延后行动族"
    return "其他"
def one(job):
    fn, ver = job
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    rep = json.load(open(fn)); nm = rep["info"]["TeamNames"]; stps = rep["steps"]
    seat = nm.index("datatuu"); o = 1 - seat
    op = fidelity.tape_agent([stps[t+1][o].get("action") or {} for t in range(len(stps)-1)])
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=rep["info"]["seed"])
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = me(obs[seat]); a[o] = op(obs[o]); g.step(a[0], a[1])
    return rep["info"]["EpisodeId"], nm[o], fam(rep, o), ver, float(g.reward(seat)-g.reward(o)), float(rep["rewards"][seat]-rep["rewards"][o])
if __name__ == "__main__":
    fs = [f for f in sorted(glob.glob(str(S/"wk2live"/"episode-*.json")))
          if json.load(open(f))["info"]["TeamNames"].count("datatuu") == 1]
    print("局数", len(fs), flush=True)
    jobs = [(f, v) for f in fs for v in ("y68wk2", "y68wk5")]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs, chunksize=2))
    json.dump([list(r) for r in res], open(S/"wk5_special.json", "w"), ensure_ascii=False)
    tab = collections.defaultdict(dict)
    for ep, opp, fm, ver, m, live in res: tab[(ep, opp, fm, live)][ver] = m
    for f2 in ("买7卖2挤压", "延后行动族", "其他"):
        v = [(k2, d) for k2, d in tab.items() if k2[2] == f2]
        if not v: continue
        w2 = sum(1 for _, d in v if d["y68wk2"] > 0); w5 = sum(1 for _, d in v if d["y68wk5"] > 0)
        wl = sum(1 for k2, _ in v if k2[3] > 0)
        print(f"{f2:8s}: {len(v)} 局 | 线上实际 {wl} 胜 | 重放 wk2 {w2} 胜 | wk5 {w5} 胜 | wk5-wk2 中位 {st.median(d['y68wk5']-d['y68wk2'] for _, d in v):+.0f}")
    allv = list(tab.values())
    print(f"合计: wk2 {sum(1 for d in allv if d['y68wk2']>0)}/{len(allv)}  wk5 {sum(1 for d in allv if d['y68wk5']>0)}/{len(allv)}")
