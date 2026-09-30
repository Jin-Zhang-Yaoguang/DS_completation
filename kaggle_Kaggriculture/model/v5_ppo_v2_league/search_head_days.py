"""Parallel all-day one-head residual scan against hard-V3.

This is a causal screening pass, not training data: each row is paired on the
same seed/seat and records a single deployable market-head intervention.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np

import base_agent
import main
from train_ppo import _fixed_opponent


ALTERNATIVES = {1: (0, 2), 2: (0, 2), 3: (0, 2), 4: (1, 2), 5: (1, 2)}


def _copy(action):
    action = action or {}
    return {"farmer": list(action.get("farmer") or ["PASS"]),
            "hands": [list(x or ["PASS"]) for x in action.get("hands", [])],
            "market": [list(x or []) for x in action.get("market", [])]}


def _play(seed, seat, candidate):
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    opponent = _fixed_opponent("v3")
    for step in range(719):
        env.state[0].observation.step = step
        env.state[1].observation.step = step
        own = candidate(env.state[seat].observation)
        other = opponent(env.state[1 - seat].observation)
        env.step([own, other] if seat == 0 else [other, own])
    rewards = [float(s.reward or 0.0) for s in env.state]
    return rewards[seat], rewards[1 - seat], [str(s.status) for s in env.state]


class OneDay:
    def __init__(self, head, value, day):
        self.head, self.value, self.day = int(head), int(value), int(day)
        self.macro = main.DEFAULT_MACRO.copy()

    def __call__(self, obs):
        step = int(obs.get("step", 0) or 0)
        day = int(obs.get("day", step // 24) or 0)
        hour = int(obs.get("hour", step % 24) or 0)
        if step == 0:
            self.macro = main.DEFAULT_MACRO.copy()
        if hour == 0:
            self.macro = main.DEFAULT_MACRO.copy()
            if day == self.day:
                self.macro[self.head] = self.value
        return main.apply_macro(obs, base_agent.agent(obs), self.macro, step)


def _task(payload):
    seed, seat, day, head, value = payload
    baseline = _play(seed, seat, base_agent.agent)
    candidate = _play(seed, seat, OneDay(head, value, day))
    b_own, b_other, b_status = baseline
    c_own, c_other, c_status = candidate
    return {"seed": int(seed), "seat": int(seat), "day": int(day), "head": int(head), "value": int(value),
            "baseline_own": b_own, "baseline_other": b_other, "own": c_own, "other": c_other,
            "uplift": c_own - b_own, "margin_uplift": (c_own - c_other) - (b_own - b_other),
            "baseline_status": b_status, "status": c_status}


def run(seed_start, seeds, days, heads, workers, output):
    seeds_list = [int(seed_start) + 101 * i for i in range(int(seeds))]
    tasks = [(seed, seat, int(day), int(head), int(value))
             for seed in seeds_list for seat in (0, 1) for day in days
             for head in heads if head in ALTERNATIVES for value in ALTERNATIVES[head]]
    context = mp.get_context("spawn")
    with context.Pool(processes=int(workers)) as pool:
        rows = list(pool.imap(_task, tasks, chunksize=1))
    summary = {}
    for row in rows:
        key = f"day{row['day']}_head{row['head']}_value{row['value']}"
        summary.setdefault(key, []).append(float(row["margin_uplift"]))
    grouped = {}
    for key, values in summary.items():
        arr = np.asarray(values, dtype=np.float64)
        rng = np.random.default_rng(20260819 + sum(map(ord, key)))
        draws = arr[rng.integers(0, len(arr), size=(3000, len(arr)))].mean(axis=1)
        grouped[key] = {"n": int(len(arr)), "mean_margin_uplift": float(arr.mean()),
                        "positive_rate": float(np.mean(arr > 0)),
                        "bootstrap_ci95": [float(np.quantile(draws, .025)), float(np.quantile(draws, .975))]}
    result = {"schema": "kaggriculture-ppo-v2-all-day-head-scan-1", "baseline": "v1", "opponent": "v3",
              "seed_start": int(seed_start), "seeds": int(seeds), "days": [int(x) for x in days],
              "heads": [int(x) for x in heads], "rows": len(rows), "errors": sum(
                  r["baseline_status"] != ["DONE", "DONE"] or r["status"] != ["DONE", "DONE"] for r in rows),
              "summary": grouped, "rows_data": rows}
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed-start", type=int, default=99400000)
    p.add_argument("--seeds", type=int, default=4)
    p.add_argument("--days", nargs="+", type=int, default=list(range(7, 29)))
    p.add_argument("--heads", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--output", type=Path, default=Path("head_day_scan_v3_4seed.json"))
    args = p.parse_args()
    result = run(args.seed_start, args.seeds, args.days, args.heads, args.workers, args.output)
    print(json.dumps({"rows": result["rows"], "errors": result["errors"], "summary_keys": len(result["summary"])}, ensure_ascii=False))
