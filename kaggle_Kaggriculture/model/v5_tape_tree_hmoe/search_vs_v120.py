"""对固定确定性对手 V120 做最优响应搜索（GA，离散参数）。
筛选集：M6 前 32 场景 × 双席位（64 局）；每代精英在全 64 场景 × 双席位复核。
日志：lib/ga_v120.log（JSON lines）；最佳：lib/ga_best.json。停止：touch lib/STOP。"""
import json, os, random, sys, time, tempfile, pathlib
HERE = pathlib.Path(__file__).resolve().parent
HARNESS = HERE.parent / "v4_demand_race" / "harness"
sys.path.insert(0, str(HARNESS))
import arena  # noqa

W = HERE.parent
V120 = str(W / "v120_hierarchical_top5_distillation" / "main.py")
CAND = str(HERE / "main.py")
SCEN = json.load(open(HARNESS / "scenarios_64.json"))
SCREEN, FULL = SCEN[:32], SCEN
LOG = HERE / "lib" / "ga_v120.log"
BEST = HERE / "lib" / "ga_best.json"
STOP = HERE / "lib" / "STOP"
PRODS = ["WOOL", "MILK", "STRAWBERRY", "MELON", "CARROT"]
SPACE = {
    "team": ["OceanMix", "V120tape", "OceanMix+V120tape"],
    "prefer_ep": ["", "104547425"],
    "lead_mode": ["no_tick", "always"],
    "shift_until": [600, 700],
    "endgame_hard": [712, 714, 716],
}
SHIFTS = [-2, -1, 0, 1, 2]
rng = random.Random(20260902)


def evaluate(genome, scen, tag):
    ov = {k: v for k, v in genome.items() if k != "shift"}
    ov["shift"] = dict(genome["shift"])
    pf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(ov, pf); pf.close()
    os.environ["V5_PARAMS"] = pf.name
    os.environ["V5_TEAM"] = genome["team"]
    rep = arena.run(CAND, {"v120": V120}, [], scenarios=scen, workers=10, out=None)["v120"]
    os.unlink(pf.name)
    return {"wr": rep["winrate"], "W": rep["W"], "L": rep["L"], "margin": rep["mean_margin"], "n": rep["games"], "tag": tag}


def fitness(r):
    return r["wr"] + r["margin"] / 1e6


def random_genome():
    g = {k: rng.choice(v) for k, v in SPACE.items()}
    g["shift"] = {p: rng.choice(SHIFTS) for p in PRODS}
    return g


def mutate(g, rate=0.3):
    h = json.loads(json.dumps(g))
    for k, v in SPACE.items():
        if rng.random() < rate:
            h[k] = rng.choice(v)
    for p in PRODS:
        if rng.random() < rate:
            h["shift"][p] = rng.choice(SHIFTS)
    return h


def crossover(a, b):
    h = json.loads(json.dumps(a))
    for k in SPACE:
        if rng.random() < 0.5:
            h[k] = b[k]
    for p in PRODS:
        if rng.random() < 0.5:
            h["shift"][p] = b["shift"][p]
    return h


def log(obj):
    with open(LOG, "a") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main():
    base = {"team": "OceanMix", "prefer_ep": "", "lead_mode": "no_tick", "shift_until": 700, "endgame_hard": 714,
            "shift": {p: 1 for p in PRODS}}
    seeds = [
        base,
        dict(base, team="V120tape", prefer_ep="104547425"),
        dict(base, team="OceanMix+V120tape", prefer_ep="104547425"),
        dict(base, shift={p: 0 for p in PRODS}),
        dict(base, shift={p: 2 for p in PRODS}, lead_mode="always"),
        dict(base, shift={p: -1 for p in PRODS}),
        dict(base, team="V120tape", prefer_ep="104547425", shift={p: 2 for p in PRODS}, lead_mode="always"),
        dict(base, team="V120tape", prefer_ep="104547425", shift={p: -1 for p in PRODS}),
    ]
    pop = [(g, None) for g in seeds] + [(random_genome(), None) for _ in range(4)]
    gen = 0
    best_full = None
    seen = {}
    while not STOP.exists():
        t0 = time.time()
        scored = []
        for g, _ in pop:
            key = json.dumps(g, sort_keys=True)
            if key in seen:
                r = seen[key]
            else:
                r = evaluate(g, SCREEN, f"g{gen}")
                seen[key] = r
                log({"gen": gen, "phase": "screen", "genome": g, **r})
            scored.append((fitness(r), g, r))
        scored.sort(key=lambda x: -x[0])
        # 精英复核（全 64 场景）
        top = scored[0]
        key = json.dumps(top[1], sort_keys=True) + "#full"
        if key not in seen:
            rf = evaluate(top[1], FULL, f"g{gen}-full")
            seen[key] = rf
            log({"gen": gen, "phase": "full", "genome": top[1], **rf})
            if best_full is None or fitness(rf) > fitness(best_full[1]):
                best_full = (top[1], rf)
                json.dump({"genome": top[1], "result": rf, "gen": gen}, open(BEST, "w"), ensure_ascii=False, indent=1)
        log({"gen": gen, "phase": "summary", "best_screen": {"wr": top[2]["wr"], "margin": top[2]["margin"]},
             "best_full": best_full[1] if best_full else None, "secs": round(time.time() - t0)})
        if best_full and best_full[1]["wr"] >= 0.80:
            log({"gen": gen, "phase": "TARGET_REACHED"})
        # 下一代：精英 3 + 交叉/变异 9
        elites = [g for _, g, _ in scored[:3]]
        nxt = [(g, None) for g in elites]
        while len(nxt) < 12:
            a, b = rng.sample(elites + [g for _, g, _ in scored[3:6]], 2)
            child = mutate(crossover(a, b))
            nxt.append((child, None))
        pop = nxt
        gen += 1
    log({"phase": "STOPPED", "gen": gen})


if __name__ == "__main__":
    main()
