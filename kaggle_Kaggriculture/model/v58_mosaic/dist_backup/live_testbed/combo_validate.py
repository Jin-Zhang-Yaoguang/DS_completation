"""按实战组合逐组合配对验证:新带 vs 旧 route0,对手 V41 与 V42(原版反应式),每组合 2 seed(座位交替)。
delta = margin(新带) - margin(route0),同 seed 同座位配对,座位偏置相消。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
def one(job):
    combo, sd, seat, var, opp = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{S}/cv_{var}_main.py")
    op = fidelity.make_agent(f"sub:{S}/kernels_0914/{opp}_agent.py")
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    combo_real = None; t = 0
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[1 - seat] = op(obs[1 - seat])
        g.step(acts[0], acts[1]); t += 1
        if t == 145:
            combo_real = "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
    return combo, sd, seat, var, opp, combo_real, g.reward(seat) - g.reward(1 - seat)
if __name__ == "__main__":
    by = json.load(open(S / "real_combo_seeds.json"))
    jobs = []
    for combo, sds in by.items():
        for i, sd in enumerate(sds[:2]):
            for var in ("newall", "oldall"):
                for opp in ("v41", "v42"):
                    jobs.append((combo, sd, i % 2, var, opp))
    res = []
    with ProcessPoolExecutor(8) as ex:
        for r in ex.map(one, jobs, chunksize=2):
            res.append(r)
    json.dump(res, open(S / "combo_validate.json", "w"))
    cell = {}
    for combo, sd, seat, var, opp, creal, m in res:
        cell[(combo, sd, seat, opp, var)] = (m, creal)
    table = {}
    for (combo, sd, seat, opp, var), (m, creal) in cell.items():
        if var != "newall": continue
        mo = cell.get((combo, sd, seat, opp, "oldall"))
        if mo is None: continue
        table.setdefault(combo, []).append((opp, sd, m - mo[0], m, mo[0], creal == combo))
    print(f"{'组合':34s} {'Δ均值':>7s} {'Δ明细(新带-route0)':s}")
    rows = []
    for combo, v in table.items():
        dm = statistics.mean(x[2] for x in v)
        rows.append((dm, combo, v))
    for dm, combo, v in sorted(rows):
        flag = "✗黑名单" if dm < 0 else ""
        print(f"{combo:34s} {dm:+7.0f} " + " ".join(f"{o}@{sd}:{d:+.0f}{'' if ok else '*'}" for o, sd, d, m, mo, ok in v) + f" {flag}")
    bl = sorted(c for dm, c, v in rows if dm < 0)
    print(f"\n建议黑名单({len(bl)} 个): {bl}")
    print("注:* 表示该局实战组合与扫描组合不一致(我方变体行为不同导致解锁不同)")
    json.dump(bl, open(S / "combo_blacklist.json", "w"))
