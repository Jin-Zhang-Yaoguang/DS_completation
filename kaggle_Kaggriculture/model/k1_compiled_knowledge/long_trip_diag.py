"""K1 长途奔走与扩地滞后诊断（vs y68g，4 seed）。
1. 每次工作前连续移动 ≥ 7 步的「长途」：终点动作、出发时携带物、途中是否经过仓库格、终点离仓距离、发生小时/日。
2. 解锁象限后空地多久被种上：每天 h12 已解锁空格数、当天 PLANT 数、种子库存、现金、目标面积与已种面积。
"""
import sys, statistics, os
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}


def one(seed):
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import importlib.util, engine, fidelity
    spec = importlib.util.spec_from_file_location(f'lt_{seed}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    opp = fidelity.make_agent(f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py')
    g = engine.load_kagsim().Game(seed=seed)
    trip = defaultdict(lambda: {"n": 0, "shed": False, "carry": None, "start": None})
    out = {"trips": [], "days": {}}
    while not engine._val(g.done):
        o0, o1 = g.observe(0), g.observe(1)
        a0 = mod.agent(o0); a1 = opp(o1)
        farm = o0["farms"][0]
        bs = len(farm["tiles"])
        sheds = set(mod._shed_tiles(bs))
        poss = [tuple(farm["farmer"])] + [tuple(h) for h in (farm.get("hands") or [])]
        invs = (o0.get("private") or {}).get("inventories") or []
        day, hour = int(o0["day"]), int(o0["hour"])
        units = [a0.get("farmer") or ["PASS"]] + list(a0.get("hands") or [])
        plants = 0
        for i, u in enumerate(units):
            op = (u or ["PASS"])[0]
            tr = trip[i]
            p = poss[i] if i < len(poss) else None
            if op in MOVES:
                if tr["n"] == 0:
                    tr["carry"] = dict(invs[i]) if i < len(invs) else {}
                    tr["start"] = p
                tr["n"] += 1
                if p in sheds:
                    tr["shed"] = True
            elif op in ("PASS",):
                continue
            else:
                if op == "PLANT":
                    plants += 1
                if tr["n"] >= 7 and op not in ("PICKUP", "DROP"):
                    out["trips"].append({"op": op if op != "PLANT" else f"PLANT_{u[1] if len(u) > 1 else ''}", "n": tr["n"],
                                         "shed": tr["shed"], "carry": ",".join(sorted(k for k, v in (tr["carry"] or {}).items() if v)),
                                         "dist": mod._shed_dist(p, bs) if p else -1, "hour": hour, "day": day})
                if op in ("PICKUP", "DROP") and tr["n"] >= 7:
                    out["trips"].append({"op": op, "n": tr["n"], "shed": True, "carry": "", "dist": 0, "hour": hour, "day": day})
                trip[i] = {"n": 0, "shed": False, "carry": None, "start": None}
        if hour == 12:
            empty = sum(1 for y, row in enumerate(farm["tiles"]) for x, t in enumerate(row)
                        if t is None and (x, y) not in sheds)
            weeds = sum(1 for row in farm["tiles"] for t in row if isinstance(t, dict) and t.get("kind") == "WEED")
            st = mod._STATE.get(0) if hasattr(mod, "_STATE") else None
            tg = sum((st or {}).get("crop_targets", {}).values()) if st else -1
            planted = sum((st or {}).get("planted", {}).values()) if st else -1
            out["days"][day] = {"empty": empty, "weeds": weeds, "quads": len(farm.get("unlocked_quadrants") or []),
                                "money": round(farm["money"]), "seeds": sum(((o0.get("private") or {}).get("seeds") or {}).values()),
                                "target": tg, "planted": planted, "hands": len(farm.get("hands") or [])}
        out["days"].setdefault(("plant", day), 0)
        out["days"][("plant", day)] = out["days"].get(("plant", day), 0) + plants
        g.step(a0, a1)
    out["days"] = {str(k): v for k, v in out["days"].items()}
    return out


def main():
    seeds = [760031 + 223 * i for i in range(4)]
    with ProcessPoolExecutor(max_workers=4) as pool:
        res = list(pool.map(one, seeds))
    trips = [t for r in res for t in r["trips"]]
    print(f"长途(≥7 步)工作 {len(trips)} 次 / 4 局（每局 {len(trips) / 4:.0f}），移动步合计每局 {sum(t['n'] for t in trips) / 4:.0f}")
    print("  终点动作:", Counter(t["op"] for t in trips).most_common(12))
    print("  途经仓库:", Counter(t["shed"] for t in trips))
    print("  出发携带:", Counter(t["carry"] or "空手" for t in trips).most_common(8))
    print("  终点离仓距离:", sorted(Counter(t["dist"] for t in trips).items()))
    print("  小时:", sorted(Counter(t["hour"] for t in trips).items()))
    print("  日:", sorted(Counter(t["day"] for t in trips).items()))
    print("\n逐日（seed0；empty=解锁空地，target/planted=作物目标/已种）")
    d = res[0]["days"]
    for day in range(0, 28):
        r = d.get(str(day))
        if r:
            print(f"  d{day:2d} 象限{r['quads']} 人手{r['hands']:2d} 空地{r['empty']:3d} 杂草{r['weeds']:2d} 目标{r['target']:3d} 已种{r['planted']:3d} "
                  f"种子{r['seeds']:3d} 现金{r['money']:6d} 当天种植{d.get(str(('plant', day)), 0)}")


if __name__ == '__main__':
    main()
