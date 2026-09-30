"""15 组合增补表独立复验:seed 1800-2039 扫描命中 → 表路线 vs 基线。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
A = HERE / "agents"
OPPS = {"V43": "kernels_0915/v43_agent.py", "V41": "kernels_0914/v41_agent.py", "V38原版": "kernels_0913/v38_main.py",
        "V43+B10": "kernels_0915/v43b10_agent.py", "V38+13/13": "opp_v38_1313_main.py", "qq型": "opp_qq_main.py"}
TAB = json.load(open(HERE / "wk2_add_table.json"))
def play(sd, seat, opp, rid, stop_at=None):
    os.environ["KAG_FORCE_ROUTE"] = str(rid)
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{A}/y68fr_main.py"); op = fidelity.make_agent(f"sub:{A}/{OPPS[opp]}")
    k = engine.load_kagsim(); g = k.Game(seed=sd); t = 0; combo = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = me(obs[seat]); a[1-seat] = op(obs[1-seat]); g.step(a[0], a[1]); t += 1
        if t == 146:
            combo = "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
            if stop_at: return combo, None
    return combo, float(g.reward(seat) - g.reward(1-seat))
def scan(job):
    sd, opp = job
    try: return (opp, sd, play(sd, sd % 2, opp, -1, stop_at=True)[0])
    except Exception: return (opp, sd, None)
def ev(job):
    sd, opp, rid = job
    try:
        c, m = play(sd, sd % 2, opp, rid); return (opp, c, rid, sd, m)
    except Exception: return (opp, None, rid, sd, None)
if __name__ == "__main__":
    seeds = list(range(1800, 2040))
    with ProcessPoolExecutor(7) as ex:
        sc = list(ex.map(scan, [(sd, o) for sd in seeds for o in OPPS], chunksize=4))
    hits = [(sd, opp, c) for opp, sd, c in sc if c in TAB]
    print("命中", len(hits), "格", flush=True)
    jobs = [(sd, opp, rid) for sd, opp, c in hits for rid in (-1, TAB[c])]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(ev, jobs, chunksize=4))
    json.dump([list(r) for r in res], open(HERE / "verify15.json", "w"))
    per = collections.defaultdict(dict)
    for opp, c, rid, sd, m in res:
        if m is not None and c: per[(opp, c, sd)][rid] = m
    tot = collections.defaultdict(lambda: [0, 0, 0, 0])
    g = b = n = w = bw = 0
    for (opp, c, sd), v in per.items():
        rid = TAB.get(c)
        if rid not in v or -1 not in v: continue
        g += v[rid]; b += v[-1]; n += 1; w += v[rid] > 0; bw += v[-1] > 0
        x = tot[c]; x[0] += v[rid] - v[-1]; x[1] += 1; x[2] += v[rid] > 0; x[3] += v[-1] > 0
    print(f"独立复验 {n} 局: 新表 {w}/{n} 总{g:+.0f} | 基线 {bw}/{n} 总{b:+.0f} | 净增 {g-b:+.0f} 每局 {(g-b)/max(1,n):+.0f}")
    for c, x in sorted(tot.items(), key=lambda kv: -kv[1][0]):
        print(f"  {c:30s} 路线{TAB[c]:4d} 净增{x[0]:+9.0f} 局{x[1]:3d} 胜 {x[2]}/{x[3]}")
