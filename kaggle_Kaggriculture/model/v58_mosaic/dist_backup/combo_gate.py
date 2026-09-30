"""每个非 YARN 组合 1 seed:y68j vs y68i 配对 + 实战组合记录。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
def one(sd):
    sys.path.insert(0, str(M / "v16_online_fidelity"))
    sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    a0 = fidelity.make_agent(f"sub:{S}/y68j_main.py")
    a1 = fidelity.make_agent(f"sub:{S}/y68i_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    combo = None; step = 0
    fb = {"farmer": ["PASS"], "hands": [], "market": []}
    while not engine._val(g.done):
        try: x = a0(g.observe(0))
        except Exception: x = dict(fb)
        try: y = a1(g.observe(1))
        except Exception: y = dict(fb)
        g.step(x, y); step += 1
        if step == 150:
            town = g.observe(0).get("town") or {}
            combo = tuple((town.get("unlocked_shops") or [])[:2])
    return sd, combo, float(engine._val(g.reward(0)) if hasattr(g,'reward') else 0), float(g.reward(0)), float(g.reward(1))
if __name__ == "__main__":
    combos = json.load(open(S / "combo_seeds.json"))
    seeds = [v[0] for v in combos.values()]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, seeds))
    rows = []
    for sd, combo, _, r0, r1 in res:
        rows.append((combo, sd, r0 - r1))
    rows.sort(key=lambda r: r[2])
    neg = 0
    for combo, sd, m in rows:
        flag = "×" if m < 0 else " "
        neg += m < 0
        print(f"{flag} {str(combo):45s} seed{sd} {m:+9.0f}")
    print(f"\n负组合 {neg}/{len(rows)}, 总和 {sum(r[2] for r in rows):+.0f}")
    json.dump([[list(c) if c else None, sd, m] for c, sd, m in rows], open(S / "combo_results.json", "w"))
