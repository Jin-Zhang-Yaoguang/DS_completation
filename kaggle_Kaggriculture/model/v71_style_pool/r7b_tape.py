"""v54live 100 局真实对手动作带:v54 vs v54r7b 并排重放。"""
import sys, json, glob, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
def one(job):
    fn, ver = job
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    r = json.load(open(fn)); nm = r["info"]["TeamNames"]; s = r["steps"]
    seat = nm.index("datatuu"); o = 1 - seat
    op = fidelity.tape_agent([s[t+1][o].get("action") or {} for t in range(len(s)-1)])
    me = fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=r["info"]["seed"])
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = me(obs[seat]); a[o] = op(obs[o]); g.step(a[0], a[1])
    return Path(fn).name, ver, float(g.reward(seat) - g.reward(o)), float(r["rewards"][seat] - r["rewards"][o])
if __name__ == "__main__":
    fs = [f for f in sorted(glob.glob(str(HERE/"v54live"/"episode-*.json")))
          if json.load(open(f))["info"]["TeamNames"].count("datatuu") == 1]
    jobs = [(f, v) for f in fs for v in ("v54", "v54r7b")]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs, chunksize=2))
    tab = collections.defaultdict(dict)
    for name, ver, m, live in res: tab[(name, live)][ver] = m
    a = sum(1 for v in tab.values() if v["v54"] > 0); b = sum(1 for v in tab.values() if v["v54r7b"] > 0)
    live_w = sum(1 for (n, lv) in tab if lv > 0)
    diff = [(k[0][:28], round(v["v54r7b"] - v["v54"])) for k, v in tab.items() if abs(v["v54r7b"] - v["v54"]) > 1]
    print(f"{len(tab)} 局: 线上实际 {live_w} 胜 | 重放 v54 {a} 胜 | v54r7b {b} 胜")
    print("变化局:", sorted(diff, key=lambda x: x[1]))
