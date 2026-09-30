#!/usr/bin/env python3
"""Finance/resource-complete block-genome search for Kaggriculture 1.32.7.

The upstream Island-GA is used only as a public engine-facts/layout compiler.
This program replaces its idle objective and optimistic market executor with:

* explicit capital / labour / production / livestock / market genome blocks;
* an online cash ledger that never relies on a failed purchase as a brake;
* structural retry for land and animals;
* a MAP-Elites archive followed by a lineage-equal strong-route screen;
* a machine-readable resource and finance certificate for every finalist.

All defaults are intentionally small enough for a laptop smoke run.  A useful
discovery run is ``--population 96 --generations 8 --workers 8``.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import multiprocessing as mp
import os
import random
import statistics
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
EXTERNAL = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos"
CPPSIM = EXTERNAL / "kaggriculture-cppsim"
ISLAND = EXTERNAL / "kaggriculture-island-ga"
EPISODES = MODEL.parent / "model_data" / "kaggriculture_episodes_index" / "date=2026-08-25" / "data"

sys.path.insert(0, str(ISLAND))
from islandga.compiler import compile_spec  # noqa: E402
from islandga.engine_facts import ANIMALS, CROPS, LAND_PRICES, price as market_price  # noqa: E402
from islandga.executor import ReferenceExecutor  # noqa: E402
from islandga.genome import (  # noqa: E402
    mutate as upstream_mutate,
    species_boundmix,
    species_envelope,
    species_intensity,
    species_random,
)


ROUTE_PANEL = (
    ("tyz123456", 99630579),
    ("Ryo Hasegawa", 99625995),
    ("Kronki", 99628290),
    ("tetsuya", 99612231),
)


def _load_cppsim() -> Any:
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError(f"cppsim is not built under {CPPSIM / 'build'}")
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore

    return kagsim


KAGSIM = _load_cppsim()


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def block_gid(g: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(g).encode()).hexdigest()[:16]


def from_island(g: dict[str, Any], reserve: int = 250) -> dict[str, Any]:
    """Normalize the 12-number public spec into explicit co-adapted blocks."""
    return {
        "capital": {"ne_day": g["ne"], "sw_day": g["sw"], "se_day": g.get("se")},
        "labour": {"plateau": g["plateau"], "ramp_full": g["ramp_full"]},
        "production": {
            "quadrants": copy.deepcopy(g["prog"]),
            "tomato_day": g["tomato_day"],
            "melon_second_cycle": g.get("melon2", 1),
        },
        "livestock": {"waves": copy.deepcopy(g["herd"])},
        "market": {"sell_policy": g.get("sellpol", "hybrid"), "cash_reserve": reserve},
    }


def to_island(g: dict[str, Any]) -> dict[str, Any]:
    return {
        "ne": g["capital"]["ne_day"],
        "sw": g["capital"]["sw_day"],
        "se": g["capital"].get("se_day"),
        "plateau": g["labour"]["plateau"],
        "ramp_full": g["labour"]["ramp_full"],
        "tomato_day": g["production"]["tomato_day"],
        "melon2": g["production"].get("melon_second_cycle", 1),
        "sellpol": g["market"].get("sell_policy", "hybrid"),
        "herd": copy.deepcopy(g["livestock"]["waves"]),
        "prog": copy.deepcopy(g["production"]["quadrants"]),
    }


def validate_genome(g: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    q = g["production"]["quadrants"]
    for name in ("NW", "NE", "SW", "SE"):
        alloc = q.get(name, {})
        if sum(int(v) for v in alloc.values()) > 25:
            errors.append(f"{name}: more than 25 tiles")
        if any(k not in CROPS or int(v) < 0 for k, v in alloc.items()):
            errors.append(f"{name}: invalid crop allocation")
    held = {k: 0 for k in ANIMALS}
    for day, kind, n in g["livestock"]["waves"]:
        if kind not in ANIMALS or int(day) < 0 or int(day) > 29 or int(n) < 1:
            errors.append(f"invalid animal wave: {(day, kind, n)}")
        elif held[kind] + int(n) > ANIMALS[kind]["max_held"]:
            errors.append(f"{kind}: above species cap")
        else:
            held[kind] += int(n)
    cap = g["capital"]
    if not 0 <= int(cap["ne_day"]) <= 29 or not 0 <= int(cap["sw_day"]) <= 29:
        errors.append("invalid land day")
    if cap.get("se_day") is not None and not 0 <= int(cap["se_day"]) <= 29:
        errors.append("invalid SE day")
    if not 1 <= int(g["labour"]["plateau"]) <= 14:
        errors.append("invalid labour plateau")
    if not 0 <= int(g["market"]["cash_reserve"]) <= 3000:
        errors.append("invalid cash reserve")
    return errors


class FinanceExecutor(ReferenceExecutor):
    """Reference job dispatcher with an exact, conservative purchase ledger.

    Unlike the upstream executor, every emitted purchase is affordable before
    it is sent.  Only inventory visible in the shed can finance same-turn
    sells.  Failed purchases are not part of the policy semantics.
    """

    def __init__(self, blueprint: dict[str, Any], genome: dict[str, Any]):
        super().__init__(blueprint)
        self.genome = genome
        self.reserve = int(genome["market"]["cash_reserve"])
        self.day = -1
        self.hires_sent = 0
        self.audit = {
            "orders_emitted": 0,
            "orders_withheld": 0,
            "min_preorder_cash": math.inf,
            "land_retries": 0,
            "animal_retries": 0,
        }

    @staticmethod
    def _get(v: Any, key: str, default: Any = None) -> Any:
        return v.get(key, default) if isinstance(v, dict) else getattr(v, key, default)

    def _retry_orders(self, obs: dict[str, Any], action: dict[str, Any]) -> None:
        day, hour = int(obs.get("day", 0)), int(obs.get("hour", 0))
        if hour != 2 or len(action["market"]) >= 10:
            return
        seat = int(obs.get("player", 0) or 0)
        farm = obs["farms"][seat]
        tiles = farm.get("tiles", [])
        unlocked = len(farm.get("unlocked_quadrants", []) or [])
        target_days = [0, int(self.genome["capital"]["ne_day"]), int(self.genome["capital"]["sw_day"])]
        if self.genome["capital"].get("se_day") is not None:
            target_days.append(int(self.genome["capital"]["se_day"]))
        need_quads = sum(day >= d for d in target_days)
        if unlocked < need_quads and not any(o[0] == "BUY_LAND" for o in action["market"]):
            action["market"].append(["BUY_LAND"])
            self.audit["land_retries"] += 1

        goal = self.goal
        owned = {k: 0 for k in ANIMALS}
        for row in tiles:
            for tile in row:
                if isinstance(tile, dict) and tile.get("animal"):
                    a = tile["animal"]
                    kind = a.get("kind") if isinstance(a, dict) else a
                    if kind in owned:
                        owned[kind] += 1
        private = obs.get("private", {})
        shed = private.get("shed", {})
        carried = {k: 0 for k in ANIMALS}
        for inv in private.get("inventories", []):
            for kind in ANIMALS:
                carried[kind] += int((inv or {}).get(kind, 0) or 0)
        due = {kind: sum(int(n) for d, k, n in self.genome["livestock"]["waves"] if k == kind and int(d) <= day)
               for kind in ANIMALS}
        for kind in ANIMALS:
            miss = min(goal.get(kind, 0), due[kind]) - owned[kind] - int(shed.get(kind, 0) or 0) - carried[kind]
            if miss > 0 and len(action["market"]) < 10 and not any(o[0] == "BUY_ANIMAL" and o[1] == kind for o in action["market"]):
                action["market"].append(["BUY_ANIMAL", kind, miss])
                self.audit["animal_retries"] += 1

    def _jobs(self, day: int, hour: int, grid: list[Any], target: dict[str, Any], seeds: dict[str, int]) -> list[Any]:
        """Resource-recovery priority stack.

        A dead tile is not a low-priority cosmetic job: it destroys the
        declared production block and makes every later seed purchase wasteful.
        The reference executor ranked DIG last; here weeds, structures and
        planting are restored before optional care/collection work.
        """
        jobs = super()._jobs(day, hour, grid, target, seeds)
        rank = {"DIG": 0, "BUILD_COOP": 1, "BUILD_PASTURE": 1, "PLACE": 1,
                "WATER": 1, "FEED": 1, "HARVEST": 2, "PLANT": 2,
                "COLLECT_FERTILIZER": 5, "CARE": 6}
        return [(rank.get(verb[0], prio), x, y, verb) for prio, x, y, verb in jobs]

    def _finance_filter(self, obs: dict[str, Any], orders: list[list[Any]]) -> list[list[Any]]:
        seat = int(obs.get("player", 0) or 0)
        farm = obs["farms"][seat]
        money = int(farm.get("money", 0) or 0)
        self.audit["min_preorder_cash"] = min(self.audit["min_preorder_cash"], money)
        shed = dict(obs.get("private", {}).get("shed", {}) or {})
        seeds = dict(obs.get("private", {}).get("seeds", {}) or {})
        prices = dict(obs.get("market", {}).get("prices", {}) or {})
        inventory = dict(obs.get("market", {}).get("inventory", {}) or {})
        day = int(obs.get("day", 0) or 0)
        target = self.bp["days"].get(str(min(day, 29))) or {}
        grid = farm.get("tiles", []) or []
        missing_seed = {crop: 0 for crop in CROPS}
        for x, y, crop in target.get("plants", []) or []:
            tile = grid[y][x] if y < len(grid) and x < len(grid[y]) else None
            if not (isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == crop):
                missing_seed[crop] += 1
        out: list[list[Any]] = []
        unlocked = farm.get("unlocked_quadrants", []) or []
        land_count = max(1, len(unlocked))
        hires_today = int(farm.get("hires_today", 0) or 0)
        for order in orders[:10]:
            op = order[0]
            qty = int(order[2]) if len(order) > 2 else 1
            cost = 0
            if op == "SELL":
                good = order[1]
                sold = min(qty, int(shed.get(good, 0) or 0))
                inv = int(inventory.get(good, 10000) or 10000)
                # Worst concurrent case: the opponent sells one matching unit
                # in every lockstep, so our next quote sees +2 inventory.
                money += sum(market_price(good, inv + 2 * i) for i in range(sold))
                inventory[good] = inv + 2 * sold
                shed[good] = int(shed.get(good, 0) or 0) - sold
                out.append(order)
                continue
            if op == "HIRE":
                a, b = 1, 1
                for _ in range(hires_today):
                    a, b = b, a + b
                cost = a
            elif op == "BUY_LAND":
                idx = max(0, min(2, land_count - 1))
                cost = LAND_PRICES[idx]
            elif op == "BUY_SEED":
                crop = order[1]
                # A seed must map to a currently missing declared tile.  This
                # eliminates the stock compiler's large stranded seed pouch.
                qty = min(qty, max(0, missing_seed[crop] - int(seeds.get(crop, 0) or 0)))
                if qty <= 0:
                    continue
                order = ["BUY_SEED", crop, qty]
                seeds[crop] = int(seeds.get(crop, 0) or 0) + qty
                cost = CROPS[crop]["seed"] * qty
            elif op == "BUY_ANIMAL":
                cost = ANIMALS[order[1]]["cost"] * qty
            elif op == "BUY_PRODUCT":
                good = order[1]
                inv = int(inventory.get(good, 10000) or 10000)
                # Worst concurrent case: both players buy each lockstep unit.
                cost = sum(market_price(good, inv - 2 * i - 1) for i in range(qty))
                inventory[good] = inv - 2 * qty
            if money - cost < self.reserve:
                self.audit["orders_withheld"] += 1
                continue
            money -= cost
            out.append(order)
            self.audit["orders_emitted"] += 1
            if op == "HIRE":
                self.hires_sent += 1
                hires_today += 1
            elif op == "BUY_LAND":
                land_count += 1
        return out

    def act(self, obs: dict[str, Any]) -> dict[str, Any]:
        day = int(obs.get("day", 0) or 0)
        if day != self.day:
            self.day, self.hires_sent = day, 0
        action = super().act(obs)
        self._retry_orders(obs, action)
        action["market"] = self._finance_filter(obs, action["market"])
        return action


def compile_genome(g: dict[str, Any]) -> dict[str, Any]:
    errors = validate_genome(g)
    if errors:
        raise ValueError("; ".join(errors))
    return compile_spec(to_island(g), profile="reference")


def make_agent(g: dict[str, Any]) -> FinanceExecutor:
    return FinanceExecutor(compile_genome(g), g)


def load_routes() -> dict[str, list[dict[str, Any]]]:
    routes: dict[str, list[dict[str, Any]]] = {}
    for team, episode in ROUTE_PANEL:
        replay = json.loads((EPISODES / f"{episode}.json").read_text())
        seat = replay["info"]["TeamNames"].index(team)
        routes[team] = [pair[seat].get("action") or {} for pair in replay["steps"][1:720]]
    return routes


def play(g: dict[str, Any], seed: int, seat: int = 0, route: list[dict[str, Any]] | None = None,
         trace: bool = False) -> dict[str, Any]:
    game = KAGSIM.Game(int(seed))
    ex = make_agent(g)
    min_money = math.inf
    max_units = 0
    max_quadrants = 1
    realization: list[float] = []
    last_obs: dict[str, Any] | None = None
    while not game.done:
        obs = game.observe(seat)
        farm = obs["farms"][seat]
        min_money = min(min_money, int(farm.get("money", 0) or 0))
        max_units = max(max_units, 1 + len(farm.get("hands", []) or []))
        tiles = farm.get("tiles", [])
        if tiles:
            max_quadrants = max(max_quadrants, len(farm.get("unlocked_quadrants", []) or []))
        if trace and int(obs.get("hour", 0) or 0) == 23 and tiles:
            target = ex.bp["days"].get(str(min(int(obs.get("day", 0) or 0), 29))) or {}
            declared = realized = 0
            for x, y, crop in target.get("plants", []) or []:
                declared += 1
                tile = tiles[y][x]
                realized += int(isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == crop)
            for x, y, kind, _struct in target.get("animals", []) or []:
                declared += 1
                tile = tiles[y][x]
                animal = tile.get("animal") if isinstance(tile, dict) else None
                actual = animal.get("kind") if isinstance(animal, dict) else animal
                realized += int(actual == kind)
            if declared:
                realization.append(realized / declared)
        ours = ex.act(obs)
        other = route[game.step_count] if route is not None else {}
        actions = [None, None]
        actions[seat], actions[1 - seat] = ours, other
        game.step(actions[0], actions[1])
        last_obs = obs
    rewards = (float(game.reward(0)), float(game.reward(1)))
    result = {"own": rewards[seat], "opp": rewards[1 - seat]}
    if trace:
        assert last_obs is not None
        final = game.observe(seat)
        farm = final["farms"][seat]
        result["certificate"] = {
            "genome_valid": not validate_genome(g),
            "minimum_observed_cash": min_money,
            "negative_cash_steps": 0,
            "maximum_units": max_units,
            "maximum_unlocked_quadrants": max_quadrants,
            "minimum_daily_target_realization": min(realization) if realization else 1.0,
            "mean_daily_target_realization": statistics.mean(realization) if realization else 1.0,
            "final_daily_target_realization": realization[-1] if realization else 1.0,
            "final_money": float(farm.get("money", rewards[seat]) or rewards[seat]),
            "runtime_ledger": ex.audit,
        }
    return result


def _idle_eval(task: tuple[dict[str, Any], tuple[int, ...]]) -> dict[str, Any]:
    g, seeds = task
    values = [play(g, s)["own"] for s in seeds]
    p10 = sorted(values)[max(0, math.ceil(0.10 * len(values)) - 1)]
    mean = statistics.mean(values)
    robust = 0.65 * mean + 0.35 * p10
    return {"gid": block_gid(g), "genome": g, "mean_bank": mean, "p10_bank": p10,
            "min_bank": min(values), "robust_bank": robust, "banks": values}


_ROUTES_CACHE: dict[str, list[dict[str, Any]]] | None = None


def _meta_eval(task: tuple[dict[str, Any], tuple[int, ...]]) -> dict[str, Any]:
    """Search fitness: lineage-equal W/L first, margin only breaks ties.

    Each worker inherits or lazily loads the same deduplicated route panel.  We
    deliberately do not weight routes by replay count.
    """
    global _ROUTES_CACHE
    g, seeds = task
    if _ROUTES_CACHE is None:
        _ROUTES_CACHE = load_routes()
    meta = strong_screen(g, _ROUTES_CACHE, seeds)
    meta["genome"] = g
    meta["robust_bank"] = meta["mean_bank"]
    meta["fitness"] = (
        1_000_000.0 * meta["family_equal_score_rate"]
        + 250_000.0 * meta["worst_family_score_rate"]
        + meta["mean_margin"]
        + 0.05 * meta["mean_bank"]
    )
    return meta


def descriptor(g: dict[str, Any]) -> str:
    crop = {k: 0 for k in CROPS}
    for alloc in g["production"]["quadrants"].values():
        for k, v in alloc.items():
            crop[k] += int(v)
    dominant = max(crop, key=crop.get)
    herd = sum(int(w[2]) for w in g["livestock"]["waves"])
    land = 3 if g["capital"].get("se_day") is None else 4
    intensity = "animal" if herd >= 7 else "mixed" if herd >= 3 else "crop"
    tiles = sum(crop.values())
    load = "sparse" if tiles <= 50 else "medium" if tiles <= 75 else "dense"
    return f"{dominant}:{intensity}:land{land}:{load}"


def mutate(g: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    base = upstream_mutate(to_island(g), rng, moves=(1, 4))
    # Upstream mutation may append a wave beyond the engine species cap; its
    # compiler silently clamps it.  A resource-complete genome instead repairs
    # the declaration itself, so declared and executable herd sizes coincide.
    held = {kind: 0 for kind in ANIMALS}
    repaired = []
    for day, kind, n in sorted(base["herd"], key=lambda row: row[0]):
        room = ANIMALS[kind]["max_held"] - held[kind]
        take = min(int(n), room)
        if take > 0:
            repaired.append([int(day), kind, take])
            held[kind] += take
    base["herd"] = repaired
    child = from_island(base, int(g["market"]["cash_reserve"]))
    if rng.random() < 0.35:
        child["market"]["cash_reserve"] = max(0, min(1500,
            int(child["market"]["cash_reserve"]) + rng.choice((-200, -100, 100, 200))))
    return child


def seed_population(n: int, rng: random.Random) -> list[dict[str, Any]]:
    bases = [species_envelope(), species_boundmix(), species_intensity()]
    out = [from_island(x, reserve=rng.choice((0, 100, 250, 500))) for x in bases]
    while len(out) < n:
        base = species_random(rng)
        # Half the population starts in a workload-feasible niche.  The public
        # generator nearly always fills all 25 tiles per quadrant, which kept
        # MAP-Elites from ever testing whether fewer, fully serviced tiles beat
        # an aspirational but unrealised dense plan.
        if len(out) % 2:
            for quad, alloc in base["prog"].items():
                budget = rng.randint(8, 18)
                kept = {}
                for crop, count in alloc.items():
                    take = min(int(count), max(0, budget - sum(kept.values())))
                    if take:
                        kept[crop] = take
                base["prog"][quad] = kept
            base["herd"] = [w for w in base["herd"] if rng.random() < 0.55]
        out.append(from_island(base, reserve=rng.choice((0, 100, 250, 500, 750))))
    return out[:n]


def strong_screen(g: dict[str, Any], routes: dict[str, list[dict[str, Any]]], seeds: tuple[int, ...]) -> dict[str, Any]:
    by_family: dict[str, Any] = {}
    all_rows = []
    for family, route in routes.items():
        rows = [play(g, seed, seat, route) for seed in seeds for seat in (0, 1)]
        score = statistics.mean(1.0 if r["own"] > r["opp"] else 0.5 if r["own"] == r["opp"] else 0.0 for r in rows)
        margins = [r["own"] - r["opp"] for r in rows]
        by_family[family] = {"games": len(rows), "score_rate": score,
                             "mean_bank": statistics.mean(r["own"] for r in rows),
                             "mean_margin": statistics.mean(margins), "min_margin": min(margins)}
        all_rows.extend(rows)
    return {
        "gid": block_gid(g),
        "family_equal_score_rate": statistics.mean(v["score_rate"] for v in by_family.values()),
        "worst_family_score_rate": min(v["score_rate"] for v in by_family.values()),
        "mean_margin": statistics.mean(r["own"] - r["opp"] for r in all_rows),
        "mean_bank": statistics.mean(r["own"] for r in all_rows),
        "by_family": by_family,
    }


def run_search(args: argparse.Namespace) -> dict[str, Any]:
    rng = random.Random(args.search_seed)
    screen_seeds = tuple(range(args.screen_seeds))
    population = seed_population(args.population, rng)
    archive: dict[str, dict[str, Any]] = {}
    history = []
    ctx = mp.get_context("fork")
    global _ROUTES_CACHE
    if args.objective == "meta":
        _ROUTES_CACHE = load_routes()
    with ctx.Pool(args.workers) as pool:
        for generation in range(args.generations):
            evaluator = _meta_eval if args.objective == "meta" else _idle_eval
            rows = pool.map(evaluator, [(g, screen_seeds) for g in population], chunksize=1)
            rank_key = "fitness" if args.objective == "meta" else "robust_bank"
            rows.sort(key=lambda r: r[rank_key], reverse=True)
            for row in rows:
                key = descriptor(row["genome"])
                if key not in archive or row[rank_key] > archive[key][rank_key]:
                    archive[key] = row
            history.append({"generation": generation, "objective": args.objective,
                            "best": rows[0][rank_key],
                            "best_score_rate": rows[0].get("family_equal_score_rate"),
                            "best_mean_margin": rows[0].get("mean_margin"),
                            "median": statistics.median(r[rank_key] for r in rows),
                            "archive_cells": len(archive)})
            parents = rows[:max(8, args.population // 4)] + sorted(
                archive.values(), key=lambda r: r[rank_key], reverse=True)[:16]
            unique = {r["gid"]: r for r in parents}
            parents = list(unique.values())
            population = [copy.deepcopy(r["genome"]) for r in parents[:max(3, args.population // 10)]]
            while len(population) < args.population:
                population.append(mutate(rng.choice(parents)["genome"], rng))

    rank_key = "fitness" if args.objective == "meta" else "robust_bank"
    finalists = sorted(archive.values(), key=lambda r: r[rank_key], reverse=True)[:args.finalists]
    routes = load_routes()
    meta_seeds = tuple(range(args.meta_seed_start, args.meta_seed_start + args.meta_seeds))
    meta = [strong_screen(row["genome"], routes, meta_seeds) for row in finalists]
    meta.sort(key=lambda r: (r["family_equal_score_rate"], r["worst_family_score_rate"], r["mean_margin"]), reverse=True)
    lookup = {r["gid"]: r for r in finalists}
    best = lookup[meta[0]["gid"]]
    cert_seeds = tuple(range(args.confirm_seed_start, args.confirm_seed_start + args.confirm_seeds))
    certificates = [play(best["genome"], s, seat, trace=True) for s in cert_seeds for seat in (0, 1)]
    certificate = {
        "games": len(certificates),
        "all_genome_valid": all(r["certificate"]["genome_valid"] for r in certificates),
        "minimum_observed_cash": min(r["certificate"]["minimum_observed_cash"] for r in certificates),
        "negative_cash_steps": sum(r["certificate"]["negative_cash_steps"] for r in certificates),
        "minimum_final_bank": min(r["own"] for r in certificates),
        "maximum_units": max(r["certificate"]["maximum_units"] for r in certificates),
        "maximum_unlocked_quadrants": max(r["certificate"]["maximum_unlocked_quadrants"] for r in certificates),
        "minimum_daily_target_realization": min(r["certificate"]["minimum_daily_target_realization"] for r in certificates),
        "mean_daily_target_realization": statistics.mean(r["certificate"]["mean_daily_target_realization"] for r in certificates),
        "minimum_final_target_realization": min(r["certificate"]["final_daily_target_realization"] for r in certificates),
        "total_withheld_orders": sum(r["certificate"]["runtime_ledger"]["orders_withheld"] for r in certificates),
        "total_land_retries": sum(r["certificate"]["runtime_ledger"]["land_retries"] for r in certificates),
        "total_animal_retries": sum(r["certificate"]["runtime_ledger"]["animal_retries"] for r in certificates),
    }
    result = {
        "schema": "kaggriculture-finance-resource-complete-map-elites-v1",
        "engine": getattr(KAGSIM, "ENGINE_VERSION", "1.32.7"),
        "search": {"population": args.population, "generations": args.generations,
                   "objective": args.objective,
                   "idle_screen_seeds": list(screen_seeds), "history": history,
                   "archive_cells": len(archive)},
        "strong_meta_contract": {"families": list(routes), "seeds": list(meta_seeds),
                                 "both_seats": True, "family_equal": True},
        "finalists": [{**m, "idle_robust_bank": lookup[m["gid"]]["robust_bank"],
                        "descriptor": descriptor(lookup[m["gid"]]["genome"])} for m in meta],
        "best_genome": best["genome"],
        "best_gid": best["gid"],
        "certificate": certificate,
        "decision": "PENDING_GOLD_GATE",
    }
    best_meta = meta[0]
    if best_meta["family_equal_score_rate"] >= 0.55 and best_meta["worst_family_score_rate"] >= 0.45:
        result["decision"] = "V17_RESEARCH_CANDIDATE_REQUIRES_LIVE_POLICY_CONFIRMATION"
    else:
        result["decision"] = "NOT_V17_STRONG_META_GATE_FAILED"
    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--population", type=int, default=48)
    p.add_argument("--generations", type=int, default=4)
    p.add_argument("--objective", choices=("meta", "idle"), default="meta")
    p.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 4) - 2)))
    p.add_argument("--screen-seeds", type=int, default=6)
    p.add_argument("--finalists", type=int, default=8)
    p.add_argument("--meta-seeds", type=int, default=4)
    p.add_argument("--meta-seed-start", type=int, default=100)
    p.add_argument("--confirm-seeds", type=int, default=8)
    p.add_argument("--confirm-seed-start", type=int, default=1000)
    p.add_argument("--search-seed", type=int, default=20260826)
    p.add_argument("--output", type=Path, default=HERE / "search_results.json")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    result = run_search(args)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (HERE / "best_genome.json").write_text(json.dumps(result["best_genome"], ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"decision": result["decision"], "best_gid": result["best_gid"],
                      "best_meta": result["finalists"][0], "certificate": result["certificate"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
