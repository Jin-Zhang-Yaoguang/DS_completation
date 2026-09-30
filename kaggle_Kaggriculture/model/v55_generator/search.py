"""参数随机搜索:3 seed solo bank 均值为目标。"""
import sys, json, random, importlib.util
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, str(Path(__file__).parent.parent / "v16_online_fidelity"))
HERE = Path(__file__).resolve().parent

SPACE = {
    "hire_per_day": [8, 10, 12, 14],
    "fert_lo": [6, 8, 10], "fert_hi": [26, 27],
    "feed_reserve": [2, 3, 4],
    "tomato_from": [10, 12, 14], "carrot_from": [21, 23, 25],
    "plant_stop": [24, 26, 27],
    "sell_every": [1, 2, 3],
    "keep_fert": [8, 15, 25],
    "prem_lot": [4, 6, 8],
    "wheat_sell_th": [10, 25, 60],
    "seed_money": [150, 300, 600],
    "feed_money": [100, 300],
    "early_hands": [6, 8, 10],
    "pasture_target": [8, 10, 12, 14],
    "animal_workers": [2, 3, 4],
    "fert_workers": [1, 2, 3],
    "coop_target": [0, 2, 4],
    "build_until": [6, 8, 11],
    "cow_until": [6, 9, 12],
    "goose_until": [10, 16, 22],
    "patrol": [0, 1],
    "share_wheat": [4, 8, 14],
    "share_straw": [18, 24, 30],
    "share_tomato": [4, 8, 12],
    "share_carrot": [6, 12, 18],
}

OPPS = {
    "ch": str(Path(__file__).parent.parent / "v51_block_router" / "newpool" / "op_e3bb880a.json"),
    "rb": str(Path(__file__).parent.parent / "v16_online_fidelity" / "tapes" / "rb_7925cb146f.json"),
    "g1": "SUB:" + str(Path(__file__).parent.parent / "v51_block_router" / "dist_v53e" / "main.py"),
    "g2": "SUB:" + str(Path(__file__).parent.parent / "v51_block_router" / "dist_v54c" / "main.py"),
}

def one(args):
    kw, sd, opp = args
    import fidelity, importlib
    spec = importlib.util.spec_from_file_location(f"sch_{sd}_{id(kw)}", HERE / "scheduler.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    sched_holder = {}
    def agent(obs, configuration=None):
        seat = obs.get("player", 0)
        t = int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))
        if t == 0 or seat not in sched_holder:
            sched_holder[seat] = m.Sched(m.Cfg(**kw))
        try:
            return sched_holder[seat].act(obs)
        except Exception:
            return {"farmer": ["PASS"], "hands": [], "market": []}
    import engine, fidelity
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    if opp and OPPS[opp].startswith("SUB:"):
        oa = fidelity.make_agent("sub:" + OPPS[opp][4:])
    elif opp:
        oa = fidelity.make_agent(f"tape:{OPPS[opp]}")
    else:
        oa = (lambda o: {"farmer": ["PASS"], "hands": [], "market": []})
    while not engine._val(g.done):
        obs = g.observe(0); obs["player"] = 0
        try:
            b = oa(g.observe(1))
        except Exception:
            b = {"farmer": ["PASS"], "hands": [], "market": []}
        g.step(agent(obs), b)
    return float(g.reward(0))

if __name__ == "__main__":
    sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
    random.seed(7)
    n_rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    best = (0, None)
    hist = []
    with ProcessPoolExecutor(6) as ex:
        for i in range(n_rounds):
            kw = {k: random.choice(v) for k, v in SPACE.items()}
            jobs = [(kw, 11, "ch"), (kw, 22, "ch"), (kw, 11, "rb"), (kw, 22, "rb"), (kw, 33, None)]
            banks = list(ex.map(one, jobs))
            avg = (sum(banks[:4]) / 4) + 0.3 * banks[4]
            hist.append((avg, kw))
            if avg > best[0]:
                best = (avg, kw)
                print(f"[{i}] avg={avg:.0f} banks={[int(b) for b in banks]} NEW BEST {json.dumps(kw)}", flush=True)
            elif i % 10 == 0:
                print(f"[{i}] avg={avg:.0f}", flush=True)
    print("BEST:", best[0], json.dumps(best[1]))
    json.dump({"avg": best[0], "cfg": best[1]}, open(HERE / "best_cfg.json", "w"))
