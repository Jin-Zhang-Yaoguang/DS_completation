"""双席位配对评测器（多进程）。

用法：
  .venv/bin/python arena.py --candidate ../main.py \
      --opponents v1am=/abs/v1_adaptive_market/main.py v76=/abs/v76/main.py \
      --seeds 101,102,... [--scenarios scenarios_64.json] [--workers 8]
输出：逐对手 W/L/T、Wilson 95% 下界、margin 均值；JSON 落盘。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _one_game(args):
    cand_path, opp_path, seed, cand_seat, shops = args
    sys.path.insert(0, str(HERE))
    from engine import fresh_agent, play
    cand = fresh_agent(cand_path)
    opp = fresh_agent(opp_path)
    if cand_seat == 0:
        b0, b1 = play(cand.agent, opp.agent, seed, shops)
        mine, theirs = b0, b1
    else:
        b0, b1 = play(opp.agent, cand.agent, seed, shops)
        mine, theirs = b1, b0
    return {"seed": seed, "seat": cand_seat, "mine": mine, "theirs": theirs,
            "margin": mine - theirs}


def wilson_lb(w, n, z=1.96):
    if n == 0:
        return 0.0
    p = w / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - r) / d


def run(candidate, opponents, seeds, scenarios=None, workers=8, out=None):
    jobs = []
    for name, opp_path in opponents.items():
        if scenarios:
            for sc in scenarios:
                for seat in (0, 1):
                    jobs.append((name, (candidate, opp_path, sc["seed"], seat, sc["shops"])))
        else:
            for seed in seeds:
                for seat in (0, 1):
                    jobs.append((name, (candidate, opp_path, seed, seat, None)))
    results = {name: [] for name in opponents}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for (name, _), res in zip(jobs, ex.map(_one_game, [j for _, j in jobs])):
            results[name].append(res)
    report = {}
    for name, rows in results.items():
        w = sum(1 for r in rows if r["margin"] > 0)
        l = sum(1 for r in rows if r["margin"] < 0)
        t = len(rows) - w - l
        n = len(rows)
        report[name] = {
            "games": n, "W": w, "L": l, "T": t,
            "winrate": round(w / n, 4) if n else 0,
            "wilson_lb": round(wilson_lb(w, n), 4),
            "mean_mine": round(sum(r["mine"] for r in rows) / n, 1) if n else 0,
            "mean_theirs": round(sum(r["theirs"] for r in rows) / n, 1) if n else 0,
            "mean_margin": round(sum(r["margin"] for r in rows) / n, 1) if n else 0,
            "rows": rows,
        }
    if out:
        Path(out).write_text(json.dumps(report, indent=1))
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--opponents", nargs="+", required=True, help="name=/abs/path/main.py")
    ap.add_argument("--seeds", default="")
    ap.add_argument("--scenarios", default=None)
    ap.add_argument("--workers", type=int, default=max(2, (os.cpu_count() or 4) - 2))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    opponents = dict(kv.split("=", 1) for kv in args.opponents)
    seeds = [int(s) for s in args.seeds.split(",") if s]
    scenarios = json.loads(Path(args.scenarios).read_text()) if args.scenarios else None
    report = run(str(Path(args.candidate).resolve()), opponents, seeds,
                 scenarios, args.workers, args.out)
    for name, r in report.items():
        print(f"{name:8s} {r['W']}/{r['L']}/{r['T']}  wr={r['winrate']:.2%} "
              f"wilsonLB={r['wilson_lb']:.2%}  mine={r['mean_mine']:.0f} "
              f"theirs={r['mean_theirs']:.0f} margin={r['mean_margin']:+.0f}")


if __name__ == "__main__":
    main()
