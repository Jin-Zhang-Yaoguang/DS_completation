#!/usr/bin/env python3
"""Minimal rolling labour planner for the production-optimizer blueprint.

The old executor greedily lets each unit take its nearest high-priority job.
It also walks inventory back to the shed shortly before midnight although the
engine atomically auto-drops every inventory at end-of-day.  This prototype
keeps the finance/market layer frozen and changes labour dispatch only:

* end-of-day auto-drop is treated as a hard engine fact;
* jobs are assigned jointly with a minimum-cost bipartite matching;
* a small persistence cost prevents units from changing targets every step;
* urgency is deadline-aware (remaining travel + one service step).

This is deliberately dependency-free at policy runtime.  scipy is used only
when available in the research harness; the bundled exact DP covers the small
worker/job matching problem otherwise.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parents[1]
OPT = RESEARCH / "production_optimizer"
sys.path.insert(0, str(OPT))
import optimizer as opt  # noqa: E402

sys.path.insert(0, str(opt.ISLAND))
from islandga.engine_facts import ANIMALS, CROPS, SHED_TILES  # noqa: E402
from islandga.executor import _dist, _shed_gate, _toward  # noqa: E402


Job = tuple[int, int, int, tuple[Any, ...]]


def _job_key(job: Job) -> tuple[Any, ...]:
    _prio, x, y, verb = job
    return (verb[0], x, y, *verb[1:])


def _exact_assignment(cost: list[list[float]]) -> list[int]:
    """O(n^2 m) Hungarian assignment for a rectangular n<=m matrix."""
    n = len(cost)
    if not n:
        return []
    m = len(cost[0])
    assert n <= m
    # 1-indexed shortest augmenting path formulation.
    u = [0.0] * (n + 1)
    v = [0.0] * (m + 1)
    p = [0] * (m + 1)
    way = [0] * (m + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [math.inf] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta, j1 = math.inf, 0
            for j in range(1, m + 1):
                if used[j]:
                    continue
                cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j], way[j] = cur, j0
                if minv[j] < delta:
                    delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    ans = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            ans[p[j] - 1] = j - 1
    return ans


class LaborPlannerExecutor(opt.FinanceExecutor):
    """Joint receding-horizon dispatcher over the compiled daily targets."""

    def __init__(self, blueprint: dict[str, Any], genome: dict[str, Any],
                 joint: bool = True, auto_drop: bool = True):
        super().__init__(blueprint, genome)
        self.joint = joint
        self.auto_drop = auto_drop
        self.assignments: dict[int, tuple[Any, ...]] = {}
        self.planner_ns = 0
        self.planner_calls = 0
        self.actions = {"service": 0, "move": 0, "pickup": 0,
                        "drop": 0, "pass": 0}

    def _same_day_sells(self, turn: int) -> dict[str, int]:
        """Only inventory needed before midnight requires an explicit DROP."""
        need: dict[str, int] = {}
        end = (turn // 24 + 1) * 24
        for t in range(turn, end):
            for order in self.bp["market"].get(str(t), ()):
                if order and order[0] == "SELL" and len(order) > 2:
                    need[order[1]] = need.get(order[1], 0) + int(order[2] or 0)
        return need

    @staticmethod
    def _deadline(job: Job, hour: int) -> int:
        op = job[3][0]
        # A plant with one missed day dies tonight; feeding/care/watering also
        # settle at midnight. Harvest/build are softer but still daily work.
        return 23 if op in {"DIG", "WATER", "FEED", "PLANT", "PLACE"} else 24

    def _job_cost(self, idx: int, pos: tuple[int, int], inv: dict[str, int],
                  job: Job, hour: int) -> float:
        prio, x, y, verb = job
        op = verb[0]
        d = _dist(pos, (x, y))
        if op == "FEED" and int(inv.get("WHEAT", 0) or 0) <= 0:
            return math.inf
        if op == "PLACE" and int(inv.get(verb[1], 0) or 0) <= 0:
            return math.inf
        slack = self._deadline(job, hour) - hour - d - 1
        late = max(0, -slack)
        urgency = max(0, 3 - slack)
        # Priority dominates distance; late jobs dominate everything.  A small
        # target persistence credit prevents symmetric workers from thrashing.
        key = _job_key(job)
        persist = -3.0 if self.assignments.get(idx) == key else 0.0
        return prio * 100.0 + late * 1000.0 + urgency * 12.0 + d + persist

    def _choose_joint(self, units: list[Any], invs: list[Any], jobs: list[Job],
                      hour: int) -> dict[int, Job]:
        feasible_jobs: list[Job] = []
        for job in jobs:
            if any(math.isfinite(self._job_cost(i, (int(u[0]), int(u[1])),
                                                dict(invs[i] or {}), job, hour))
                   for i, u in enumerate(units) if u):
                feasible_jobs.append(job)
        # Only the best n jobs can be executed next; ranking includes urgency
        # and the nearest feasible unit, hence it is a one-step time-expanded
        # min-cost-flow approximation rather than a local nearest-job rule.
        ranked = sorted(
            feasible_jobs,
            key=lambda j: min(self._job_cost(i, (int(u[0]), int(u[1])),
                                             dict(invs[i] or {}), j, hour)
                              for i, u in enumerate(units) if u),
        )
        n, r = len(units), len(ranked)
        matrix: list[list[float]] = []
        for i, u in enumerate(units):
            pos = (int(u[0]), int(u[1]))
            inv = dict(invs[i] or {}) if i < len(invs) else {}
            row = [self._job_cost(i, pos, inv, job, hour) for job in ranked]
            # Private dummy PASS columns. Passing is worse than any feasible
            # real job but cheaper than an impossible one.
            row.extend([50_000.0 if j == i else math.inf for j in range(n)])
            matrix.append(row)
        picks = _exact_assignment(matrix)
        return {i: ranked[j] for i, j in enumerate(picks) if j < r}

    def _choose_greedy(self, units: list[Any], invs: list[Any], jobs: list[Job],
                       hour: int) -> dict[int, Job]:
        chosen: dict[int, Job] = {}
        claimed: set[tuple[Any, ...]] = set()
        for i, u in enumerate(units):
            pos = (int(u[0]), int(u[1]))
            inv = dict(invs[i] or {}) if i < len(invs) else {}
            candidates = [(self._job_cost(i, pos, inv, job, hour), job)
                          for job in jobs if _job_key(job) not in claimed]
            if candidates:
                cost, job = min(candidates, key=lambda row: row[0])
                if math.isfinite(cost):
                    chosen[i] = job
                    claimed.add(_job_key(job))
        return chosen

    def act(self, obs: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter_ns()
        seat = int(obs.get("player", 0) or 0)
        day, hour = int(obs.get("day", 0) or 0), int(obs.get("hour", 0) or 0)
        turn = day * 24 + hour
        if day != self.day:
            self.day, self.hires_sent = day, 0
            self.assignments.clear()

        farm = obs["farms"][seat]
        grid = farm.get("tiles", []) or []
        private = obs.get("private", {}) or {}
        seeds = dict(private.get("seeds", {}) or {})
        shed = dict(private.get("shed", {}) or {})
        invs = list(private.get("inventories", []) or [])
        units = [farm.get("farmer")] + list(farm.get("hands", []) or [])
        while len(invs) < len(units):
            invs.append({})
        carried: dict[str, int] = {}
        for inv in invs:
            for good, qty in dict(inv or {}).items():
                carried[good] = carried.get(good, 0) + int(qty or 0)

        market = self._market_orders(turn, grid, shed, carried)
        target = self.bp["days"].get(str(min(day, 29))) or {}
        jobs = [tuple((p, x, y, tuple(v))) for p, x, y, v
                in self._jobs(day, hour, grid, target, seeds)]

        # Preserve the inherited daily seed makeup valve.
        if hour == 3 and day < 26 and len(market) < 10:
            money = float(farm.get("money", 0) or 0)
            want: dict[str, int] = {}
            for x, y, crop in target.get("plants", ()):
                if y < len(grid) and x < len(grid[y]) and grid[y][x] is None:
                    want[crop] = want.get(crop, 0) + 1
            for crop, qty in sorted(want.items()):
                miss = qty - int(seeds.get(crop, 0) or 0)
                cost = CROPS[crop]["seed"]
                if miss > 0 and money >= miss * cost + 300:
                    buy = min(miss, 6)
                    market.append(["BUY_SEED", crop, buy])
                    money -= buy * cost
            market = market[:10]

        # Same-day sales are the only reason to explicitly return inventory.
        sells = self._same_day_sells(turn) if self.auto_drop else self._upcoming_sells(turn)
        short = {g: n - int(shed.get(g, 0) or 0) for g, n in sells.items()
                 if n > int(shed.get(g, 0) or 0)}

        # Feeders without wheat require a shed mission. Animal placement uses
        # the same mechanism, one unit per missing kind at a time.
        synthetic: dict[int, list[Any]] = {}
        unfed = sum(1 for _p, _x, _y, verb in jobs if verb[0] == "FEED")
        wheat_carriers = sum(int(dict(inv or {}).get("WHEAT", 0) or 0) for inv in invs)
        if unfed and not wheat_carriers and int(shed.get("WHEAT", 0) or 0) > 0:
            best = min(range(len(units)), key=lambda i: _dist(tuple(units[i]), _shed_gate(tuple(units[i]))))
            pos = tuple(units[best])
            synthetic[best] = (["PICKUP", "WHEAT", min(unfed, int(shed["WHEAT"]), 6)]
                               if pos in SHED_TILES else _toward(pos, _shed_gate(pos)))

        # Likewise, move a bought animal from the shed to a waiting structure.
        for _p, _x, _y, verb in jobs:
            if verb[0] != "PLACE":
                continue
            kind = verb[1]
            if int(shed.get(kind, 0) or 0) <= 0 or any(int(dict(iv or {}).get(kind, 0) or 0) > 0 for iv in invs):
                continue
            candidates = [i for i in range(len(units)) if i not in synthetic]
            if candidates:
                best = min(candidates, key=lambda i: _dist(tuple(units[i]), _shed_gate(tuple(units[i]))))
                pos = tuple(units[best])
                synthetic[best] = (["PICKUP", kind, 1] if pos in SHED_TILES
                                   else _toward(pos, _shed_gate(pos)))
            break

        # A carrier needed by an imminent same-day sell preempts field work.
        for i, u in enumerate(units):
            if i in synthetic:
                continue
            inv = dict(invs[i] or {})
            if any(int(inv.get(g, 0) or 0) > 0 for g in short):
                for g in list(short):
                    short[g] -= int(inv.get(g, 0) or 0)
                    if short[g] <= 0:
                        del short[g]
                pos = tuple(u)
                synthetic[i] = ["DROP"] if pos in SHED_TILES else _toward(pos, _shed_gate(pos))

        # Zero-travel work underfoot is throughput-dominant. Reserve it before
        # global matching, preserving the engine's valuable opportunism.
        preassigned: dict[int, Job] = {}
        claimed_here: set[tuple[Any, ...]] = set()
        for i, u in enumerate(units):
            if i in synthetic:
                continue
            pos = tuple(u)
            inv = dict(invs[i] or {})
            here = [(self._job_cost(i, pos, inv, job, hour), job) for job in jobs
                    if (job[1], job[2]) == pos and _job_key(job) not in claimed_here]
            if here:
                cost, job = min(here, key=lambda row: row[0])
                if math.isfinite(cost):
                    preassigned[i] = job
                    claimed_here.add(_job_key(job))
        remaining_jobs = [job for job in jobs if _job_key(job) not in claimed_here]
        free_indices = [i for i in range(len(units)) if i not in synthetic and i not in preassigned]
        free_units = [units[i] for i in free_indices]
        free_invs = [invs[i] for i in free_indices]
        assignments_local = (self._choose_joint(free_units, free_invs, remaining_jobs, hour)
                             if self.joint else self._choose_greedy(free_units, free_invs, remaining_jobs, hour))
        assignments = dict(preassigned)
        assignments.update({free_indices[i]: job for i, job in assignments_local.items()})

        verbs: list[list[Any]] = []
        live_keys = {_job_key(job) for job in jobs}
        for i, u in enumerate(units):
            pos = (int(u[0]), int(u[1]))
            if i in synthetic:
                verb = synthetic[i]
            elif i in assignments:
                job = assignments[i]
                _p, x, y, task = job
                self.assignments[i] = _job_key(job)
                verb = list(task) if pos == (x, y) else _toward(pos, (x, y))
            else:
                old = self.assignments.get(i)
                if old not in live_keys:
                    self.assignments.pop(i, None)
                inv = dict(invs[i] or {})
                load = sum(int(v or 0) for v in inv.values())
                # For next-day hour-0 sales, midnight auto-drop is free. Only
                # unload when the shed must sell later in the current day.
                if load > 0 and not self.auto_drop and hour >= 20:
                    verb = ["DROP"] if pos in SHED_TILES else _toward(pos, _shed_gate(pos))
                else:
                    verb = ["PASS"]
            op = verb[0]
            if op in {"NORTH", "SOUTH", "EAST", "WEST"}:
                self.actions["move"] += 1
            elif op == "PICKUP":
                self.actions["pickup"] += 1
            elif op == "DROP":
                self.actions["drop"] += 1
            elif op == "PASS":
                self.actions["pass"] += 1
            else:
                self.actions["service"] += 1
            verbs.append(verb)

        action = {"farmer": verbs[0] if verbs else ["PASS"],
                  "hands": verbs[1:], "market": market}
        self._retry_orders(obs, action)
        action["market"] = self._finance_filter(obs, action["market"])
        self.planner_ns += time.perf_counter_ns() - started
        self.planner_calls += 1
        return action


def make_executor(genome: dict[str, Any], mode: str) -> opt.FinanceExecutor:
    bp = opt.compile_genome(genome)
    if mode == "stock":
        return opt.FinanceExecutor(bp, genome)
    if mode == "autodrop_greedy":
        return LaborPlannerExecutor(bp, genome, joint=False, auto_drop=True)
    if mode == "joint_mpc":
        return LaborPlannerExecutor(bp, genome, joint=True, auto_drop=True)
    raise ValueError(mode)


def play(genome: dict[str, Any], seed: int, seat: int, mode: str,
         route: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    game = opt.KAGSIM.Game(seed)
    ex = make_executor(genome, mode)
    realization: list[float] = []
    miss = Counter()
    runtime_ns = 0
    calls = 0
    while not game.done:
        obs = game.observe(seat)
        if int(obs.get("hour", 0) or 0) == 23:
            farm = obs["farms"][seat]
            grid = farm.get("tiles", []) or []
            target = ex.bp["days"].get(str(min(int(obs.get("day", 0) or 0), 29))) or {}
            declared = realized = 0
            for x, y, crop in target.get("plants", ()):
                declared += 1
                tile = grid[y][x]
                ok = isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == crop
                realized += int(ok)
                if not ok:
                    if tile is None:
                        miss["plant_empty"] += 1
                    elif isinstance(tile, dict) and tile.get("kind") == "WEED":
                        miss["plant_weed"] += 1
                    elif isinstance(tile, dict) and tile.get("kind") == "PLANT":
                        miss["plant_wrong_crop"] += 1
                    else:
                        miss["plant_other"] += 1
            for x, y, kind, _struct in target.get("animals", ()):
                declared += 1
                tile = grid[y][x]
                animal = tile.get("animal") if isinstance(tile, dict) else None
                actual = animal.get("kind") if isinstance(animal, dict) else animal
                ok = actual == kind
                realized += int(ok)
                if not ok:
                    miss["animal_missing"] += 1
            if declared:
                realization.append(realized / declared)
        t0 = time.perf_counter_ns()
        ours = ex.act(obs)
        runtime_ns += time.perf_counter_ns() - t0
        calls += 1
        actions = [{}, {}]
        actions[seat] = ours
        if route is not None:
            actions[1 - seat] = route[game.step_count]
        game.step(actions[0], actions[1])
    cert = {
        "mean_daily_target_realization": statistics.mean(realization),
        "minimum_daily_target_realization": min(realization),
        "final_daily_target_realization": realization[-1],
        "runtime_us_per_call": runtime_ns / max(1, calls) / 1000,
        "hour23_target_misses": dict(miss),
    }
    if isinstance(ex, LaborPlannerExecutor):
        cert["action_counts"] = ex.actions
    return {"mode": mode, "seed": seed, "seat": seat,
            "bank": float(game.reward(seat)),
            "opponent_bank": float(game.reward(1 - seat)),
            "certificate": cert}


def main() -> None:
    genome = json.loads((OPT / "best_genome.json").read_text())
    rows = []
    seeds = list(range(5000, 5012))
    for seed in seeds:
        for seat in (0, 1):
            for mode in ("stock", "autodrop_greedy", "joint_mpc"):
                rows.append(play(genome, seed, seat, mode))
    summary = {}
    for mode in ("stock", "autodrop_greedy", "joint_mpc"):
        sub = [r for r in rows if r["mode"] == mode]
        summary[mode] = {
            "episodes": len(sub),
            "mean_bank": statistics.mean(r["bank"] for r in sub),
            "mean_daily_target_realization": statistics.mean(r["certificate"]["mean_daily_target_realization"] for r in sub),
            "minimum_final_target_realization": min(r["certificate"]["final_daily_target_realization"] for r in sub),
            "runtime_us_per_call": statistics.mean(r["certificate"]["runtime_us_per_call"] for r in sub),
        }
    payload = {"schema": "kaggriculture-labor-planner-prototype-v1",
               "seeds": seeds, "both_seats": True,
               "fixed_genome": str(OPT / "best_genome.json"),
               "summary": summary, "episodes": rows}
    (HERE / "prototype_results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
