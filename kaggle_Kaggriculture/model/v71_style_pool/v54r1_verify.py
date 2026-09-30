"""v54r1 表独立复验:seed 9300-9399 × V52/V53,扫描命中表内组合 → 表路线 vs 基线。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
TAB = {k: v for k, v in json.load(open(HERE/"v54r1_table_draft.json")).items()}
def play(opp, seed, rid, stop=False):
    os.environ["KAG_FORCE_ROUTE"] = str(rid)
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{HERE}/agents/v54fr_main.py")
    op = fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=seed); t = 0; combo = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; g.step(me(obs[0]), op(obs[1])); t += 1
        if t == 146:
            combo = "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
            if stop: return combo, None
    return combo, float(g.reward(0) - g.reward(1))
def scan(job):
    opp, sd = job
    try: return opp, sd, play(opp, sd, -1, stop=True)[0]
    except Exception: return opp, sd, None
def ev(job):
    opp, sd, rid = job
    try:
        c, m = play(opp, sd, rid); return opp, sd, rid, c, m
    except Exception: return opp, sd, rid, None, None
if __name__ == "__main__":
    with ProcessPoolExecutor(7) as ex:
        sc = list(ex.map(scan, [(o, s) for o in ("v52", "v53") for s in range(9300, 9400)], chunksize=3))
    hits = [(o, s, c) for o, s, c in sc if c in TAB]
    print("命中", len(hits), flush=True)
    jobs = [(o, s, r) for o, s, c in hits for r in (-1, TAB[c])]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(ev, jobs, chunksize=3))
    json.dump([list(r) for r in res], open(HERE/"v54r1_verify.json", "w"))
    per = collections.defaultdict(dict)
    for o, s, r, c, m in res:
        if m is not None: per[(o, s, c)][r] = m
    g = b = n = w = bw = 0; byc = collections.defaultdict(lambda: [0, 0, 0])
    for (o, s, c), v in per.items():
        rid = TAB[c]
        if rid not in v or -1 not in v: continue
        g += v[rid]; b += v[-1]; n += 1; w += v[rid] > 0; bw += v[-1] > 0
        x = byc[c]; x[0] += (v[rid] > 0) - (v[-1] > 0); x[1] += v[rid] - v[-1]; x[2] += 1
    print(f"复验 {n} 局: 新表 {w} 胜 | 基线 {bw} 胜 | 净增 {g-b:+.0f}")
    for c, x in sorted(byc.items(), key=lambda kv: -kv[1][0]):
        print(f"  {c:30s} 路线{TAB[c]:4d} 胜差{x[0]:+d} 净增{x[1]:+9.0f} 局{x[2]}")
