"""FM 验证 v2:按对手使用各自扫描出的 FM seed,逐局记录真实组合,按真实组合统计。
用法: python fm_validate2.py 版本1,版本2"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
VERS = sys.argv[1].split(",")
OPPS = {"V43": "kernels_0915/v43_agent.py", "V41": "kernels_0914/v41_agent.py", "V38原版": "kernels_0913/v38_main.py",
        "V43+B10": "kernels_0915/v43b10_agent.py", "V38+13/13": "opp_v38_1313_main.py", "qq型": "opp_qq_main.py"}
def one(job):
    sd, seat, ver, opp = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py"); op = fidelity.make_agent(f"sub:{S}/{OPPS[opp]}")
    k = engine.load_kagsim(); g = k.Game(seed=sd); t = 0; combo = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[1 - seat] = op(obs[1 - seat])
        g.step(acts[0], acts[1]); t += 1
        if t == 146: combo = "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
    return sd, seat, ver, opp, combo, g.reward(seat) - g.reward(1 - seat)
if __name__ == "__main__":
    by_opp = json.load(open(S / "combo_seeds_by_opp.json"))
    v43scan = {}
    for f in ("combo_seeds_y68v.json", "combo_seeds_y68v_b.json"):
        for c, v in json.load(open(S / f)).items(): v43scan.setdefault(c, []).extend(v)
    seeds_for = {"V43": v43scan, "V41": v43scan, "qq型": by_opp["V38原版"], "V38原版": by_opp["V38原版"],
                 "V43+B10": by_opp["V43+B10"], "V38+13/13": by_opp["V38+13/13"]}
    jobs = []
    for opp in OPPS:
        fm = {c: v for c, v in seeds_for[opp].items() if "FARMERS_MARKET" in c.split("|")}
        for c, sds in fm.items():
            for i, sd in enumerate(sds[:8]):
                for ver in VERS: jobs.append((sd, i % 2, ver, opp))
    print(f"任务 {len(jobs)} 局", flush=True)
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=4))
    json.dump(res, open(S / f"fm_validate2_{'_'.join(VERS)}.json", "w"), ensure_ascii=False)
    fm_res = [r for r in res if r[4] and "FARMERS_MARKET" in r[4].split("|")]
    print(f"真实组合为 FM 的局 {len(fm_res)}/{len(res)}")
    combos = sorted({r[4] for r in fm_res})
    for ver in VERS:
        print(f"\n===== {ver}(按真实组合)=====")
        print(f"{'组合':32s} " + " ".join(f"{o:>13s}" for o in OPPS))
        tot = {o: [0, 0] for o in OPPS}
        for c in combos:
            cells = []
            for o in OPPS:
                vals = [r[5] for r in fm_res if r[2] == ver and r[3] == o and r[4] == c]
                if not vals: cells.append("-"); continue
                w = sum(x > 0 for x in vals); tot[o][0] += w; tot[o][1] += len(vals)
                cells.append(f"{w}/{len(vals)}{'' if w == len(vals) else '✗'} {min(vals):+.0f}")
            print(f"{c:32s} " + " ".join(f"{x:>13s}" for x in cells))
        print(f"{'合计':32s} " + " ".join(f"{tot[o][0]:>5d}/{tot[o][1]:<6d}" for o in OPPS))
