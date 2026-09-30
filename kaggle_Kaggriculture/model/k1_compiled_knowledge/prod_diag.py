"""产出侧诊断：草莓成熟面积/每成熟格·天产量/施肥与浇水、动物数与照料喂养、逐日人手动作分解（d15-19 断档）。

用法: /opt/anaconda3/bin/python3 prod_diag.py [n_majkel] [n_k1]
"""
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

from scale_distill import HERE, IDX, V71, MOS  # noqa: F401

MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
STRAW_MATURE = 10


def stats(obs_seq, act_seq, seat):
    d = defaultdict(lambda: Counter())
    for obs, act in zip(obs_seq, act_seq):
        if not obs or not act:
            continue
        day, hour = int(obs.get("day", 0)), int(obs.get("hour", 0))
        c = d[day]
        farm = (obs.get("farms") or [{}, {}])[seat]
        tiles = farm.get("tiles") or []
        poss = [farm.get("farmer")] + list(farm.get("hands") or [])
        prices = (obs.get("market") or {}).get("prices") or {}
        units = [act.get("farmer") or ["PASS"]] + list(act.get("hands") or [])
        c["unit_steps"] += len(units)
        for i, u in enumerate(units):
            op = (u or ["PASS"])[0]
            if op in MOVES:
                c["a_MOVE"] += 1
            elif op in ("PICKUP", "DROP"):
                c["a_CARRY"] += 1
            else:
                c["a_" + op] += 1
            if op == "HARVEST" and i < len(poss) and poss[i]:
                x, y = poss[i]
                try:
                    t = tiles[y][x]
                except (IndexError, TypeError):
                    t = None
                if isinstance(t, dict):
                    key = t.get("crop") if t.get("kind") == "PLANT" else t.get("animal")
                    c["hu_" + str(key)] += t.get("yield_units") or 0
        for o in act.get("market") or []:
            if o and o[0] == "SELL" and len(o) >= 3:
                c["rev"] += int(o[2] or 0) * prices.get(o[1], 0)
        if hour in (12, 21):
            tag = "h12" if hour == 12 else "h21"
            for row in tiles:
                for t in row:
                    if not isinstance(t, dict):
                        continue
                    k = t.get("kind")
                    if k == "PLANT" and t.get("crop") == "STRAWBERRY" and tag == "h12":
                        c["st_days"] += 1
                        if day - t.get("planted_day", day) >= STRAW_MATURE:
                            c["st_mature"] += 1
                            if (t.get("fertilized_until_day") or -1) >= day:
                                c["st_mature_fert"] += 1
                        if (t.get("consecutive_unwatered") or 0) > 0:
                            c["st_dry"] += 1
                    elif k == "PLANT" and tag == "h21":
                        c["pl21"] += 1
                        if not t.get("watered_today"):
                            c["pl21_unwatered"] += 1
                    elif k in ("PASTURE", "COOP") and t.get("animal"):
                        a = t["animal"]
                        if tag == "h12":
                            c["an_" + a] += 1
                            c["an_bonus"] += t.get("pending_care_bonus") or 0
                            if (t.get("consecutive_unfed") or 0) > 0:
                                c["an_unfed"] += 1
                        else:
                            c["an21"] += 1
                            c["an21_uncared"] += 0 if t.get("cared_today") else 1
                            c["an21_unfed"] += 0 if t.get("fed_today") else 1
    return {k: dict(v) for k, v in d.items()}


def majkel_one(line):
    g = json.loads(line)
    fp = IDX / g["date"] / "data" / f"{g['ep']}.json"
    if not fp.exists():
        return None
    rep = json.loads(fp.read_text())
    names = (rep.get("info") or {}).get("TeamNames") or []
    if "Majkel1337" not in names:
        return None
    seat = names.index("Majkel1337")
    steps = rep.get("steps") or []
    return stats([steps[t - 1][seat].get("observation") for t in range(1, len(steps))],
                 [steps[t][seat].get("action") for t in range(1, len(steps))], seat)


def k1_one(seed):
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import importlib.util
    import engine
    import fidelity
    t0 = time.time()
    spec = importlib.util.spec_from_file_location(f"k1_pd_{seed}", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    opp = fidelity.make_agent(f"sub:{MOS}/y68g_main.py")
    g = engine.load_kagsim().Game(seed=seed)
    obs_seq, act_seq = [], []
    while not (g.done() if callable(g.done) else g.done):
        o0, o1 = g.observe(0), g.observe(1)
        a0 = mod.agent(o0)
        try:
            a1 = opp(o1)
        except Exception:
            a1 = {"farmer": ["PASS"], "hands": [], "market": []}
        obs_seq.append(o0)
        act_seq.append(a0)
        g.step(a0, a1)
    r = stats(obs_seq, act_seq, 0)
    r["_sec"] = time.time() - t0
    return r


SEGS = [(0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30)]


def seg_med(games, lo, hi, f):
    vals = []
    for g in games:
        agg = Counter()
        for dd in range(lo, hi):
            agg.update(g.get(dd, {}))
        vals.append(f(agg))
    return statistics.median(vals)


def ratio(a, b):
    return a / b if b else 0


def main():
    n_mj = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    n_k1 = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    lines = []
    with open(V71 / "majkel_0910_12.jsonl") as f:
        for line in f:
            if '"date=2026-09-10"' in line[:200]:
                continue
            lines.append(line)
            if len(lines) >= n_mj:
                break
    with ProcessPoolExecutor(max_workers=8) as pool:
        mj = [r for r in pool.map(majkel_one, lines) if r]
        k1 = list(pool.map(k1_one, [1046 + 137 * i for i in range(n_k1)]))
    secs = [g.pop("_sec") for g in k1]
    k1 = [{int(k): v for k, v in g.items()} for g in k1]
    G = {"M": mj, "K": k1}
    rows = [
        ("卖出收入", lambda a: a["rev"]),
        ("草莓面积·天", lambda a: a["st_days"]),
        ("草莓成熟格·天", lambda a: a["st_mature"]),
        ("草莓收获单位", lambda a: a["hu_STRAWBERRY"]),
        ("单位/成熟格·天", lambda a: ratio(a["hu_STRAWBERRY"], a["st_mature"])),
        ("成熟草莓施肥率", lambda a: ratio(a["st_mature_fert"], a["st_mature"])),
        ("草莓缺水率", lambda a: ratio(a["st_dry"], a["st_days"])),
        ("h21未浇作物率", lambda a: ratio(a["pl21_unwatered"], a["pl21"])),
        ("牛·天", lambda a: a["an_COW"]),
        ("羊·天", lambda a: a["an_SHEEP"]),
        ("奶/牛·天", lambda a: ratio(a["hu_COW"], a["an_COW"])),
        ("毛/羊·天", lambda a: ratio(a["hu_SHEEP"], a["an_SHEEP"])),
        ("h21未照料率", lambda a: ratio(a["an21_uncared"], a["an21"])),
        ("h21未喂率", lambda a: ratio(a["an21_unfed"], a["an21"])),
        ("人手步数", lambda a: a["unit_steps"]),
        ("MOVE 占比", lambda a: ratio(a["a_MOVE"], a["unit_steps"])),
        ("PASS 占比", lambda a: ratio(a["a_PASS"], a["unit_steps"])),
        ("HARVEST", lambda a: a["a_HARVEST"]),
        ("WATER", lambda a: a["a_WATER"]),
        ("PLANT", lambda a: a["a_PLANT"]),
        ("FERTILIZE", lambda a: a["a_FERTILIZE"]),
        ("COLLECT_FERT", lambda a: a["a_COLLECT_FERTILIZER"]),
        ("FEED", lambda a: a["a_FEED"]),
        ("CARE", lambda a: a["a_CARE"]),
        ("CARRY", lambda a: a["a_CARRY"]),
        ("BUILD+DIG", lambda a: a["a_BUILD_PASTURE"] + a["a_BUILD_COOP"] + a["a_DIG"]),
    ]
    print(f"Majkel {len(mj)} 局 / K1 {len(k1)} 局（中位数，每 5 天段，M/K）；K1 单局耗时中位 {statistics.median(secs):.1f}s")
    print(f"{'指标':<14}" + "".join(f"| d{lo:>2}-{hi - 1:<2}           " for lo, hi in SEGS))
    out = {}
    for name, f in rows:
        cells = []
        for lo, hi in SEGS:
            m, k = seg_med(G["M"], lo, hi, f), seg_med(G["K"], lo, hi, f)
            out.setdefault(name, []).append([m, k])
            fmt = "{:.2f}" if max(abs(m), abs(k)) < 5 else "{:.0f}"
            cells.append(f"| {fmt.format(m):>7}/{fmt.format(k):<9}")
        print(f"{name:<14}" + "".join(cells))
    (HERE / "prod_diag_result.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
