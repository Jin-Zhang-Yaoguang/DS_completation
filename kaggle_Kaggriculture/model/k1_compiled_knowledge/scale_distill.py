"""规模蒸馏：Majkel vs K1 逐日 空地/各作物面积/种植次数/买种/买动物。

用法: /opt/anaconda3/bin/python3 scale_distill.py [n_majkel] [n_k1]
"""
import importlib.util
import json
import statistics
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
V71 = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v71_majkel_reverse")
IDX = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
MOS = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v58_mosaic/dist_backup"
CROPS = ("WHEAT", "MELON", "STRAWBERRY", "CARROT", "TOMATO")


def day_rows(obs_seq, act_seq, seat):
    """每天 h12 快照 + 全天动作计数。"""
    rows = defaultdict(lambda: {"plant": 0, "seed": Counter(), "animal": Counter()})
    for obs, act in zip(obs_seq, act_seq):
        if not obs or not act:
            continue
        farm = (obs.get("farms") or [{}, {}])[seat]
        tiles = farm.get("tiles") or []
        if not tiles:
            continue
        day, hour = int(obs.get("day", 0)), int(obs.get("hour", 0))
        r = rows[day]
        for u in [act.get("farmer") or ["PASS"]] + list(act.get("hands") or []):
            if u and u[0] == "PLANT":
                r["plant"] += 1
        for o in act.get("market") or []:
            if o and o[0] == "BUY_SEED" and len(o) >= 3:
                r["seed"][o[1]] += int(o[2] or 0)
            elif o and o[0] == "BUY_ANIMAL" and len(o) >= 2:
                r["animal"][o[1]] += int(o[2]) if len(o) >= 3 else 1
        if hour == 12:
            empty = locked = struct = 0
            area = Counter()
            for row in tiles:
                for t in row:
                    if t is None:
                        empty += 1
                    elif t == "LOCKED":
                        locked += 1
                    elif isinstance(t, dict):
                        if t.get("kind") == "PLANT":
                            area[t.get("crop")] += 1
                        elif t.get("kind") in ("PASTURE", "COOP"):
                            struct += 1
            r["empty"], r["locked"], r["struct"], r["area"] = empty, locked, struct, area
    return {d: dict(v) for d, v in rows.items()}


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
    return day_rows([steps[t - 1][seat].get("observation") for t in range(1, len(steps))],
                    [steps[t][seat].get("action") for t in range(1, len(steps))], seat)


def k1_one(seed):
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import engine
    import fidelity
    spec = importlib.util.spec_from_file_location(f"k1_sd_{seed}", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    opp = fidelity.make_agent(f"sub:{MOS}/y68g_main.py")
    k = engine.load_kagsim()
    g = k.Game(seed=seed)
    obs_seq, act_seq = [], []
    fb = {"farmer": ["PASS"], "hands": [], "market": []}
    while not (g.done() if callable(g.done) else g.done):
        o0, o1 = g.observe(0), g.observe(1)
        a0 = mod.agent(o0)
        try:
            a1 = opp(o1)
        except Exception:
            a1 = dict(fb)
        obs_seq.append(o0)
        act_seq.append(a0)
        g.step(a0, a1)
    return day_rows(obs_seq, act_seq, 0)


def summarize(games):
    out = {}
    for d in range(30):
        rs = [g[d] for g in games if d in g and "empty" in g[d]]
        if not rs:
            continue
        med = lambda f: statistics.median(f(r) for r in rs)
        out[d] = {
            "empty": med(lambda r: r["empty"]),
            "unlocked": med(lambda r: 100 - r["locked"]),
            "struct": med(lambda r: r["struct"]),
            "area": {c: med(lambda r, c=c: r["area"].get(c, 0)) for c in CROPS},
            "plant": med(lambda r: r["plant"]),
            "seed": med(lambda r: sum(r["seed"].values())),
            "animal": med(lambda r: sum(r["animal"].values())),
        }
    return out


def main():
    n_mj = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    n_k1 = int(sys.argv[2]) if len(sys.argv) > 2 else 6
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
    M, K = summarize(mj), summarize(k1)
    print(f"Majkel {len(mj)} 局 / K1 {len(k1)} 局（中位数，h12 快照 + 全天计数）")
    print(f"{'d':>2} | {'空地 M/K':>9} | {'解锁 M/K':>9} | {'栏 M/K':>7} | {'种植 M/K':>8} | {'买种 M/K':>9} | {'买畜 M/K':>7} | 面积 M(麦/瓜/莓/萝/番) | 面积 K")
    for d in range(30):
        m, k = M.get(d), K.get(d)
        if not m or not k:
            continue
        ma = "/".join(f"{m['area'][c]:.0f}" for c in CROPS)
        ka = "/".join(f"{k['area'][c]:.0f}" for c in CROPS)
        print(f"{d:2d} | {m['empty']:4.0f}/{k['empty']:<4.0f} | {m['unlocked']:4.0f}/{k['unlocked']:<4.0f} | "
              f"{m['struct']:3.0f}/{k['struct']:<3.0f} | {m['plant']:3.0f}/{k['plant']:<4.0f} | "
              f"{m['seed']:4.0f}/{k['seed']:<4.0f} | {m['animal']:3.0f}/{k['animal']:<3.0f} | {ma:>17s} | {ka}")
    (HERE / "scale_distill_result.json").write_text(json.dumps({"majkel": M, "k1": K}, indent=1, default=str))


if __name__ == "__main__":
    main()
