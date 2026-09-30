"""用户双指标:①y68s vs y68 家族各 16 局(8 seed × 2 席位);②轨迹重合度(farmer/hands 分段,2 seed)。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
FAM = ["y68a", "y68c", "y68f", "y68g", "y68h", "y68i", "y68j", "y68r2"]
SEEDS = [1100, 1101, 1104, 1108, 1109, 1111, 1115, 1129]
def play(job):
    opp, sd, flip = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity
    a, b = f"sub:{S}/y68v_main.py", f"sub:{S}/{opp}_main.py"
    if flip: a, b = b, a
    r = fidelity.play(a, b, sd, [])
    m = r["bank"][0] - r["bank"][1]
    return "win", opp, sd, flip, (-m if flip else m)
def overlap(job):
    opp, sd = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    a0 = fidelity.make_agent(f"sub:{S}/y68v_main.py"); a1 = fidelity.make_agent(f"sub:{S}/{opp}_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=sd); A, B = [], []
    while not engine._val(g.done):
        x, y = a0(g.observe(0)), a1(g.observe(1))
        A.append(json.dumps({"f": x.get("farmer"), "h": x.get("hands")}, sort_keys=True))
        B.append(json.dumps({"f": y.get("farmer"), "h": y.get("hands")}, sort_keys=True))
        g.step(x, y)
    seg = {}
    for lab, (i, j) in (("t1-144", (0, 144)), ("145-360", (144, 360)), ("361-600", (360, 600)), ("601-末", (600, len(A))), ("全程", (0, len(A)))):
        seg[lab] = sum(p == q for p, q in zip(A[i:j], B[i:j])) / max(1, j - i)
    return "ov", opp, sd, None, seg
def job(j): return play(j) if j[0] == "p" else overlap(j[1:])
if __name__ == "__main__":
    jobs = [("p", o, sd, f) for o in FAM for sd in SEEDS for f in (False, True)]
    ov_jobs = [("o", o, sd) for o in FAM for sd in (1100, 1108)]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(lambda j: None, [])) or []
    with ProcessPoolExecutor(8) as ex:
        wins = list(ex.map(play, [j[1:] for j in jobs], chunksize=2))
        ovs = list(ex.map(overlap, [j[1:] for j in ov_jobs]))
    print("① 胜率(每对 16 局)")
    print(f"{'对手':6s} {'胜':>3s} {'平':>3s} {'负':>3s} {'胜率(除平)':>9s} {'中位margin':>10s} {'min':>8s} {'max':>8s}")
    for o in FAM:
        v = [w[4] for w in wins if w[1] == o]
        w_ = sum(x > 0 for x in v); d = sum(x == 0 for x in v); l = sum(x < 0 for x in v)
        print(f"{o:6s} {w_:3d} {d:3d} {l:3d} {w_/max(1,len(v)-d):9.0%} {statistics.median(v):+10.0f} {min(v):+8.0f} {max(v):+8.0f}")
    print("\n② 轨迹重合度")
    print(f"{'对手':6s} {'seed':>5s} {'t1-144':>7s} {'145-360':>8s} {'361-600':>8s} {'601-末':>7s} {'全程':>6s}")
    for _, o, sd, _, s in ovs:
        print(f"{o:6s} {sd:5d} {s['t1-144']:7.2f} {s['145-360']:8.2f} {s['361-600']:8.2f} {s['601-末']:7.2f} {s['全程']:6.2f}")
