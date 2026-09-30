import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
TAB = {"BRUNCH_SPOT|YARN_STORE": 103, "SMOOTHIE_SHOP|FARMERS_MARKET": 110, "PIZZA_SHOP|ICE_CREAM_SHOP": 107}
def play(seed, rid, stop=False):
    os.environ["KAG_FORCE_ROUTE"] = str(rid)
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{HERE}/agents/v54fr_main.py")
    op = fidelity.make_agent(f"sub:{HERE}/agents/v54_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=seed); t = 0; combo = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; g.step(me(obs[0]), op(obs[1])); t += 1
        if t == 146:
            combo = "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
            if stop: return combo, None
    return combo, float(g.reward(0) - g.reward(1))
def scan(sd):
    try: return sd, play(sd, -1, stop=True)[0]
    except Exception: return sd, None
def ev(job):
    sd, rid = job
    try:
        c, m = play(sd, rid); return sd, rid, c, m
    except Exception: return sd, rid, None, None
if __name__ == "__main__":
    with ProcessPoolExecutor(7) as ex: sc = list(ex.map(scan, range(9400, 9520), chunksize=3))
    hits = [(s, c) for s, c in sc if c in TAB]
    print("V54 镜像命中", len(hits), flush=True)
    jobs = [(s, r) for s, c in hits for r in (-1, TAB[c])]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(ev, jobs, chunksize=3))
    per = collections.defaultdict(dict)
    for s, r, c, m in res:
        if m is not None: per[(s, c)][r] = m
    g = b = n = w = bw = 0
    for (s, c), v in per.items():
        rid = TAB[c]
        if rid not in v or -1 not in v: continue
        g += v[rid]; b += v[-1]; n += 1; w += v[rid] > 0; bw += v[-1] > 0
    print(f"镜像族 {n} 局: 新表 {w} 胜 | 基线 {bw} 胜 | 净增 {g-b:+.0f}")
