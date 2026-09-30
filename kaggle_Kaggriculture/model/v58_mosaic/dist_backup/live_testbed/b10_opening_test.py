"""B10 家族赢我们靠什么:5 个 B10 线上 seed(线上席位),我方 y68r2 / y68k 对阵 V43 原版 vs V43+B10/S10 开局 vs V42+B10/S10。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
OLD = "_R42_OPENING=[['BUY_PRODUCT', 'WHEAT', 5], ['BUY_PRODUCT', 'WHEAT', 10], ['SELL', 'WHEAT', 60]]"
NEW = "_R42_OPENING=[['BUY_PRODUCT', 'WHEAT', 10], ['BUY_PRODUCT', 'WHEAT', 0], ['SELL', 'WHEAT', 10]]"
def build():
    for name, path in (("v43b10", S / "kernels_0915/v43_agent.py"), ("v42b10", S / "kernels_0914/v42_agent.py")):
        src = path.read_text(); assert OLD in src, name
        (S / f"kernels_0915/{name}_agent.py").write_text(src.replace(OLD, NEW))
def one(job):
    eid, me_file, opp = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    rep = json.load(open(S / f"live_replays3/episode-{eid}-replay.json"))
    nm = rep["info"]["TeamNames"]; seat = nm.index("datatuu"); o = 1 - seat
    opath = {"v43": "kernels_0915/v43_agent.py", "v43b10": "kernels_0915/v43b10_agent.py", "v42b10": "kernels_0915/v42b10_agent.py"}[opp]
    me = fidelity.make_agent(f"sub:{S}/{me_file}"); op = fidelity.make_agent(f"sub:{S}/{opath}")
    k = engine.load_kagsim(); g = k.Game(seed=rep["info"]["seed"])
    h30 = None; t = 0
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[o] = op(obs[o])
        g.step(acts[0], acts[1]); t += 1
        if t == 30:
            f = g.observe(0)["farms"]; h30 = (len(f[seat].get("hands") or []), len(f[o].get("hands") or []))
    return eid, str(nm[o]), me_file, opp, h30, g.reward(seat) - g.reward(o), rep["rewards"][seat] - rep["rewards"][o]
if __name__ == "__main__":
    build()
    ids = json.load(open(S / "ep_ids8.json"))
    pick = set()
    for tag in ids:
        for eid in ids[tag]:
            p = S / f"live_replays3/episode-{eid}-replay.json"
            if not p.exists(): continue
            rep = json.load(open(p)); nm = rep["info"]["TeamNames"]
            if nm.count("datatuu") != 1: continue
            o = 1 - nm.index("datatuu")
            m1 = (rep["steps"][1][o].get("action") or {}).get("market") or []
            if sum(int(x[2]) for x in m1 if x and x[0] == "BUY_PRODUCT" and len(x) > 2) == 10: pick.add(eid)
    jobs = [(e, f, o) for e in sorted(pick) for f in ("y68r2_main.py", "y68k_main.py") for o in ("v43", "v43b10", "v42b10")]
    res = []
    with ProcessPoolExecutor(6) as ex:
        res = list(ex.map(one, jobs))
    for e in sorted(pick):
        rows = [r for r in res if r[0] == e]
        print(f"\nep{e} vs {rows[0][1]} 线上 {rows[0][6]:+.0f}")
        for r in rows:
            print(f"   我={r[2]:14s} 对手={r[3]:7s} day1帮工(我,彼)={r[4]} margin {r[5]:+.0f}")
    print("\n汇总(5 seed 胜局 / 总 margin):")
    for f in ("y68r2_main.py", "y68k_main.py"):
        for o in ("v43", "v43b10", "v42b10"):
            v = [r[5] for r in res if r[2] == f and r[3] == o]
            print(f"   {f:14s} vs {o:7s}: {sum(x>0 for x in v)}/{len(v)} 总 {sum(v):+.0f}")
