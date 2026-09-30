"""CEM 参数搜索：在 kagsim 上对 meta 代表打双席位，最大化 margin。

用法：.venv/bin/python search/cem.py [--gens 20] [--pop 24] [--workers 9]
结果写 search/cem_state.json（可断点续跑）与 search/cem_best.json。
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
V4 = HERE.parent
W = V4.parent.parent            # kaggle_Kaggriculture/
sys.path.insert(0, str(V4 / "harness"))

# 参数空间：name -> (lo, hi, is_int)
SPACE = {
    "n_animal_tiles":   (8, 16, True),
    "n_wheat_tiles":    (2, 8, True),
    "n_melon_tiles":    (8, 20, True),
    "n_straw_tiles":    (6, 20, True),
    "n_melon2_tiles":   (0, 8, True),
    "herd_sheep":       (1, 4, True),
    "herd_cow":         (6, 12, True),
    "early_sheep":      (0, 3, True),
    "early_cow":        (1, 5, True),
    "ipo_day":          (7, 13, True),
    "hands0":           (3, 8, True),
    "hands2":           (6, 12, True),
    "hands10":          (8, 14, True),
    "land_ne":          (2, 9, True),
    "land_sw":          (7, 14, True),
    "last_animal_day":  (12, 20, True),
    "slip_tol":         (0.03, 0.15, False),
    "premium_wait_margin": (1.02, 1.20, False),
    "glut_floor_frac":  (0.30, 0.70, False),
    "batch_cap":        (6, 16, True),
    "feed_stock_days":  (1, 4, True),
    "wheat_hoard_until_day": (6, 16, True),
    "terminal_turn":    (680, 706, True),
    "sell_late_day":    (17, 26, True),
    "forced_flush":     (0, 1, True),
    "assign_dist_w":    (0.5, 3.0, False),
}
KEYS = sorted(SPACE)


def vec_to_policy(v):
    d = dict(zip(KEYS, v))
    ov = {}
    for k in ("n_animal_tiles", "n_wheat_tiles", "n_melon_tiles", "n_straw_tiles",
              "n_melon2_tiles", "ipo_day", "last_animal_day", "slip_tol",
              "premium_wait_margin", "glut_floor_frac", "batch_cap",
              "feed_stock_days", "wheat_hoard_until_day", "terminal_turn",
              "sell_late_day", "forced_flush", "assign_dist_w"):
        ov[k] = d[k]
    ov["herd"] = [("SHEEP", d["herd_sheep"]), ("COW", d["herd_cow"])]
    ov["herd_early"] = [("SHEEP", d["early_sheep"]), ("COW", d["early_cow"])]
    ov["hands_schedule"] = [(0, d["hands0"]), (2, d["hands2"]), (10, d["hands10"])]
    ov["buy_land_days"] = {"NE": d["land_ne"], "SW": d["land_sw"]}
    return ov


def _clip(v):
    out = []
    for k, x in zip(KEYS, v):
        lo, hi, is_int = SPACE[k]
        x = min(hi, max(lo, x))
        out.append(int(round(x)) if is_int else x)
    return out


def evaluate(args):
    vec, seeds, opp_name = args
    import importlib.util
    sys.path.insert(0, str(V4 / "harness"))
    from engine import load_kagsim, _val
    k = load_kagsim()
    opp_path = {"v1am": W / "model/v1_adaptive_market/main.py",
                "v76": W / "model/v76_adjacent_safe_buy_lead/main.py"}[opp_name]

    def fresh(path):
        spec = importlib.util.spec_from_file_location(f"m{random.random()}", path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    ov = vec_to_policy(vec)
    margins, mines = [], []
    for seed in seeds:
        for seat in (0, 1):
            c = fresh(V4 / "main.py")
            c.POLICY.update(ov)
            o = fresh(opp_path)
            g = k.Game(seed=seed)
            ags = [c.agent, o.agent] if seat == 0 else [o.agent, c.agent]
            while not _val(g.done):
                g.step(ags[0](g.observe(0)), ags[1](g.observe(1)))
            mine, theirs = g.reward(seat), g.reward(1 - seat)
            margins.append(mine - theirs)
            mines.append(mine)
    return statistics.mean(margins) + 0.15 * statistics.mean(mines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gens", type=int, default=20)
    ap.add_argument("--pop", type=int, default=24)
    ap.add_argument("--elite", type=int, default=6)
    ap.add_argument("--workers", type=int, default=9)
    ap.add_argument("--opp", default="v1am")
    ap.add_argument("--state", default=str(HERE / "cem_state.json"))
    args = ap.parse_args()

    rng = random.Random(20260901)
    state_p = Path(args.state)
    if state_p.exists():
        st = json.loads(state_p.read_text())
        mu, sigma, gen0 = st["mu"], st["sigma"], st["gen"]
    else:
        # 均值从当前 POLICY 出发
        import importlib.util
        spec = importlib.util.spec_from_file_location("cur", V4 / "main.py")
        cur = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cur)
        P = cur.POLICY
        base = {
            "herd_sheep": P["herd"][0][1], "herd_cow": P["herd"][1][1],
            "early_sheep": P["herd_early"][0][1], "early_cow": P["herd_early"][1][1],
            "hands0": P["hands_schedule"][0][1], "hands2": P["hands_schedule"][1][1],
            "hands10": P["hands_schedule"][-1][1],
            "land_ne": P["buy_land_days"]["NE"], "land_sw": P["buy_land_days"]["SW"],
        }
        mu = [float(base.get(k, P.get(k, (SPACE[k][0] + SPACE[k][1]) / 2))) for k in KEYS]
        sigma = [(SPACE[k][1] - SPACE[k][0]) / 4 for k in KEYS]
        gen0 = 0

    for gen in range(gen0, args.gens):
        seeds = [rng.randrange(1, 10 ** 6) for _ in range(3)]
        pop = []
        for _ in range(args.pop):
            v = [rng.gauss(m, s) for m, s in zip(mu, sigma)]
            pop.append(_clip(v))
        pop[0] = _clip(list(mu))                       # 精英保底：当前均值
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            fits = list(ex.map(evaluate, [(v, seeds, args.opp) for v in pop]))
        ranked = sorted(zip(fits, pop), key=lambda z: -z[0])
        elite = [v for _, v in ranked[:args.elite]]
        mu = [statistics.mean(v[i] for v in elite) for i in range(len(KEYS))]
        sigma = [max(0.02 * (SPACE[k][1] - SPACE[k][0]),
                     statistics.pstdev([v[i] for v in elite]) * 1.1)
                 for i, k in enumerate(KEYS)]
        best_fit, best_v = ranked[0]
        print(f"gen {gen:>3} best={best_fit:>10.0f} mean={statistics.mean(fits):>10.0f} "
              f"| {json.dumps(vec_to_policy(best_v), default=str)[:150]}", flush=True)
        state_p.write_text(json.dumps({"mu": mu, "sigma": sigma, "gen": gen + 1}))
        (HERE / "cem_best.json").write_text(json.dumps(
            {"fit": best_fit, "vec": best_v, "policy": vec_to_policy(best_v)},
            indent=1, default=str))


if __name__ == "__main__":
    main()
