"""按对手扫实战商店组合:y68x vs {V38原版, V43+B10, V38+13/13},seed 3000-4799,跑到 t146。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
OPPS = {"V38原版": "kernels_0913/v38_main.py", "V43+B10": "kernels_0915/v43b10_agent.py", "V38+13/13": "opp_v38_1313_main.py"}
def one(job):
    opp, sd = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    a = fidelity.make_agent(f"sub:{S}/y68x_main.py"); b = fidelity.make_agent(f"sub:{S}/{OPPS[opp]}")
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    for _ in range(146):
        g.step(a(g.observe(0)), b(g.observe(1)))
    return opp, sd, "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
if __name__ == "__main__":
    jobs = [(o, sd) for o in OPPS for sd in range(3000, 4800)]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=16))
    base = {}
    for f in ("combo_seeds_y68v.json", "combo_seeds_y68v_b.json"):
        for c, v in json.load(open(S / f)).items():
            for sd in v: base[sd] = c
    out = {}
    for opp, sd, c in res:
        out.setdefault(opp, {}).setdefault(c, []).append(sd)
    json.dump(out, open(S / "combo_seeds_by_opp.json", "w"), ensure_ascii=False)
    for opp in OPPS:
        same = sum(1 for o, sd, c in res if o == opp and base.get(sd) == c)
        fm = {c: v for c, v in out[opp].items() if "FARMERS_MARKET" in c.split("|")}
        print(f"{opp}: 与 V43 扫描组合一致 {same}/1800;FM 组合 {len(fm)} 种 {sum(len(v) for v in fm.values())} seed")
