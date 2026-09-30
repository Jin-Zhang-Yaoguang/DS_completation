import sys, json, glob, statistics as st
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
    k = engine.load_kagsim(); g = k.Game(seed=r["info"]["seed"]); tom = 0
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = me(obs[seat]); a[o] = op(obs[o])
        for c in [a[seat].get("farmer")] + list(a[seat].get("hands") or []):
            if c and c[:2] == ["PLANT", "TOMATO"]: tom += 1
        g.step(a[0], a[1])
    return Path(fn).name, ver, float(g.reward(seat) - g.reward(o)), tom
if __name__ == "__main__":
    hits = []
    for fn in sorted(glob.glob(str(HERE/"wk5live"/"episode-*.json"))):
        r = json.load(open(fn)); nm = r["info"]["TeamNames"]
        if nm.count("datatuu") != 1: continue
        shops = (r["steps"][360][0]["observation"].get("town") or {}).get("unlocked_shops") or []
        if sum(x in ("PIZZA_SHOP", "FARMERS_MARKET") for x in shops) >= 2: hits.append(fn)
    jobs = [(f, v) for f in hits for v in ("y68wk5", "y68tm")]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs, chunksize=2))
    tab = {}
    for name, ver, m, tom in res: tab.setdefault(name, {})[ver] = (m, tom)
    d = [(v["y68tm"][0] - v["y68wk5"][0], v["y68tm"][1], v["y68wk5"][0]) for v in tab.values()]
    trig = [x for x in d if x[1] > 0]
    print(f"命中 {len(tab)} 局,实际触发 {len(trig)} 局")
    print(f"触发局净增: 中位 {st.median(x[0] for x in trig):+.0f} 均值 {sum(x[0] for x in trig)/len(trig):+.0f} 分布 {sorted(round(x[0]) for x in trig)}")
    w5 = sum(1 for x in d if x[2] > 0); wt = sum(1 for x in d if x[2] + x[0] > 0)
    print(f"41 局胜负: wk5 {w5} → tm {wt}")
