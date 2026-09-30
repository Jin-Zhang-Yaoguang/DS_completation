#!/usr/bin/env python3
"""Causal information-value screen for complete-route portfolios.

Development proxy dates (2026-08-20..22) and seed range are frozen before
evaluation.  Held-out proxy dates (2026-08-23..24) and disjoint seeds are used
exactly once.  Replay tails are fixed-stream upper bounds, not live-policy
evidence.  In particular, features observed after step 72 are explicitly
labelled unavailable to the current day-3 router.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[5]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
INDEX = ROOT / "kaggle_Kaggriculture" / "model_data" / "kaggriculture_episodes_index"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
SOURCE = INDEX / "date=2026-08-25" / "data"

TEAMS = ("Crop Dusta", "Ryo Hasegawa", "Subramanya N", "tetsuya", "Kronki", "tyz123456")
PREFIX_ID = "tyz123456::99609968"
V17_IDS = ("tyz123456::99609968", "Kronki::99596430")
DEV_PROXIES = (
    ("2026-08-20", "Ryo Hasegawa", 94854181),
    ("2026-08-20", "SaiKushal185", 95531759),
    ("2026-08-21", "Subramanya N", 96275739),
    ("2026-08-21", "James Holland", 95908394),
    ("2026-08-22", "Arman Tuganbaev", 96925631),
    ("2026-08-22", "Excluding", 96651843),
)
TEST_PROXIES = (
    ("2026-08-23", "Crop Dusta", 97710447),
    ("2026-08-23", "MiMi", 97687527),
    ("2026-08-24", "Kronki", 98486063),
    ("2026-08-24", "taiseiu", 98463302),
)
DEV_SEEDS = range(0, 160)
TEST_SEEDS = range(30000, 30160)
ITEMS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")


def runtime():
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError("cppsim build missing")
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    return kagsim


KAGSIM = runtime()


def route(day: str, team: str, episode: int) -> dict:
    path = INDEX / f"date={day}" / "data" / f"{episode}.json"
    replay = json.loads(path.read_text())
    seat = replay["info"]["TeamNames"].index(team)
    actions = [copy.deepcopy(pair[seat].get("action") or {}) for pair in replay["steps"][1:720]]
    return {
        "id": f"{team}::{episode}", "team": team, "episode": episode, "date": day,
        "actions": actions,
        "behavior_sha256": hashlib.sha256(json.dumps(actions, sort_keys=True).encode()).hexdigest(),
    }


def candidate_routes() -> list[dict]:
    rows = []
    for team in TEAMS:
        found = []
        for path in SOURCE.glob("*.json"):
            if json.dumps(team) in path.open(errors="ignore").read(5000):
                found.append(int(path.stem))
        for episode in sorted(found, reverse=True)[:3]:
            rows.append(route("2026-08-25", team, episode))
    if not all(any(row["id"] == target for row in rows) for target in V17_IDS):
        raise RuntimeError("V17 route missing")
    return rows


def tile_counts(farm: dict) -> dict:
    out = defaultdict(int)
    for line in farm["tiles"]:
        for tile in line:
            if isinstance(tile, dict):
                out[str(tile.get("kind", "UNKNOWN"))] += 1
                if tile.get("animal"):
                    out["ANIMAL"] += 1
    return out


def public_features(obs: dict, seat: int, tag: str) -> dict[str, float]:
    opponent = obs["farms"][1 - seat]
    counts = tile_counts(opponent)
    prices = obs["market"]["prices"]
    inventory = obs["market"]["inventory"]
    result = {
        f"{tag}_opp_money": float(opponent["money"]),
        f"{tag}_opp_hands": float(len(opponent["hands"])),
        f"{tag}_opp_land": float(len(opponent["unlocked_quadrants"])),
        f"{tag}_opp_plants": float(counts.get("PLANT", 0)),
        f"{tag}_opp_animals": float(counts.get("ANIMAL", 0)),
        f"{tag}_opp_weeds": float(counts.get("WEED", 0)),
        f"{tag}_market_total_depletion": float(sum(10000 - int(inventory[x]) for x in ITEMS)),
    }
    for item in ITEMS:
        result[f"{tag}_price_{item}"] = float(prices[item])
        result[f"{tag}_depletion_{item}"] = float(10000 - int(inventory[item]))
    return result


def observe_shared(prefix: list[dict], opponent: list[dict], seed: int, seat: int) -> dict:
    game = KAGSIM.Game(seed)
    captured = {}
    for step in range(145):
        if step in (72, 120, 144):
            obs = game.observe(seat)
            shops = list(obs["town"]["unlocked_shops"])
            captured.update(public_features(obs, seat, f"s{step}"))
            captured[f"shop{step}"] = shops[-1] if shops else "NO_SHOP"
            if step == 144:
                captured["shop_pair"] = "|".join(shops[:2])
        if step < 144:
            pair = [None, None]
            pair[seat] = prefix[step]
            pair[1 - seat] = opponent[step]
            game.step(pair[0], pair[1])
    return captured


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def run_table(routes: list[dict], proxies: tuple, seeds: range, split: str, branch_step: int) -> list[dict]:
    prefix = next(row for row in routes if row["id"] == PREFIX_ID)["actions"]
    rows, jobs, labels = [], [], []
    for day, team, episode in proxies:
        opp = route(day, team, episode)
        family = f"{day}::{team}::{episode}"
        for seed in seeds:
            for seat in (0, 1):
                features = observe_shared(prefix, opp["actions"], seed, seat)
                for candidate in routes:
                    actions = prefix[:branch_step] + candidate["actions"][branch_step:]
                    if seat == 0:
                        jobs.append((KAGSIM.Stream(actions), KAGSIM.Stream(opp["actions"]), seed))
                    else:
                        jobs.append((KAGSIM.Stream(opp["actions"]), KAGSIM.Stream(actions), seed))
                    labels.append((candidate, family, day, team, episode, seed, seat, features))
    rewards = KAGSIM.run_many(jobs)
    for label, reward in zip(labels, rewards, strict=True):
        candidate, family, day, team, episode, seed, seat, features = label
        own, other = float(reward[seat]), float(reward[1 - seat])
        rows.append({
            "split": split, "branch_step": branch_step, "route": candidate["id"],
            "family": family, "date": day, "opponent_team": team, "opponent_episode": episode,
            "seed": seed, "seat": seat, "own": own, "opp": other,
            "margin": own - other, "game_score": score(own - other), **features,
        })
    return rows


def summarize(rows: list[dict]) -> dict:
    margins = sorted(float(row["margin"]) for row in rows)
    n = max(1, math.ceil(len(margins) * 0.10))
    by_family = defaultdict(list)
    for row in rows:
        by_family[row["family"]].append(row)
    fam_scores = [statistics.mean(x["game_score"] for x in group) for group in by_family.values()]
    return {
        "games": len(rows),
        "score_rate": statistics.mean(row["game_score"] for row in rows),
        "family_equal_score_rate": statistics.mean(fam_scores),
        "worst_family_score_rate": min(fam_scores),
        "mean_bank": statistics.mean(float(row["own"]) for row in rows),
        "mean_margin": statistics.mean(margins),
        "margin_p10": margins[max(0, math.ceil(len(margins) * 0.10) - 1)],
        "margin_cvar10": statistics.mean(margins[:n]),
    }


def game_groups(rows: list[dict], subset: list[str]) -> dict[tuple, list[dict]]:
    groups = defaultdict(list)
    allowed = set(subset)
    for row in rows:
        if row["route"] in allowed:
            groups[(row["family"], row["seed"], row["seat"])].append(row)
    return groups


def choose_best(group: list[dict]) -> dict:
    return max(group, key=lambda row: (row["game_score"], row["margin"], row["own"]))


def train_lookup(rows: list[dict], subset: list[str], key_fields: tuple[str, ...], fallback: dict | None = None) -> dict:
    cells = defaultdict(list)
    for row in rows:
        if row["route"] in subset:
            key = tuple(str(row[field]) for field in key_fields)
            cells[(key, row["route"])].append(row)
    choices = {}
    keys = sorted({key for key, _ in cells})
    for key in keys:
        candidates = []
        for rid in subset:
            values = cells.get((key, rid), [])
            if values:
                candidates.append((
                    statistics.mean(x["game_score"] for x in values),
                    statistics.mean(x["margin"] for x in values), rid,
                ))
        if candidates:
            choices[key] = max(candidates)[2]
    return {"fields": key_fields, "choices": choices, "fallback": fallback}


def apply_lookup(rows: list[dict], subset: list[str], model: dict) -> list[dict]:
    groups = game_groups(rows, subset)
    selected = []
    for group in groups.values():
        exemplar = group[0]
        key = tuple(str(exemplar[field]) for field in model["fields"])
        rid = model["choices"].get(key)
        if rid is None and model.get("fallback"):
            fallback = model["fallback"]
            fkey = tuple(str(exemplar[field]) for field in fallback["fields"])
            rid = fallback["choices"].get(fkey)
        if rid is None:
            rid = subset[0]
        selected.append(next(row for row in group if row["route"] == rid))
    return selected


def best_single(dev: list[dict], subset: list[str]) -> str:
    candidates = []
    for rid in subset:
        metric = summarize([row for row in dev if row["route"] == rid])
        candidates.append((metric["family_equal_score_rate"], metric["worst_family_score_rate"], metric["mean_margin"], rid))
    return max(candidates)[-1]


def oracle_rows(rows: list[dict], subset: list[str]) -> list[dict]:
    return [choose_best(group) for group in game_groups(rows, subset).values()]


def quantile_thresholds(values: list[float]) -> list[float]:
    values = sorted(set(values))
    if len(values) < 4:
        return values[:-1]
    return sorted(set(values[min(len(values) - 1, int((len(values) - 1) * q))] for q in (0.2, 0.4, 0.6, 0.8)))


def train_public_stump(dev: list[dict], subset: list[str], step: int, base_model: dict) -> dict:
    numeric = [key for key in dev[0] if key.startswith(f"s{step}_")]
    best = None
    for feature in numeric:
        values = [float(row[feature]) for row in dev if row["route"] == subset[0]]
        for threshold in quantile_thresholds(values):
            tagged = []
            for row in dev:
                item = dict(row)
                item["stump_bin"] = "L" if float(row[feature]) <= threshold else "H"
                tagged.append(item)
            model = train_lookup(tagged, subset, ("shop72", "stump_bin"), fallback=base_model)
            selected = apply_lookup(tagged, subset, model)
            metric = summarize(selected)
            rank = (metric["family_equal_score_rate"], metric["worst_family_score_rate"], metric["mean_margin"])
            if best is None or rank > best[0]:
                best = (rank, feature, threshold, model, metric)
    assert best
    return {"feature": best[1], "threshold": best[2], "lookup": best[3], "dev": best[4]}


def apply_public_stump(rows: list[dict], subset: list[str], stump: dict) -> list[dict]:
    tagged = []
    for row in rows:
        item = dict(row)
        item["stump_bin"] = "L" if float(row[stump["feature"]]) <= stump["threshold"] else "H"
        tagged.append(item)
    return apply_lookup(tagged, subset, stump["lookup"])


def recovery(policy: dict, baseline: dict, oracle: dict) -> dict:
    score_gap = oracle["family_equal_score_rate"] - baseline["family_equal_score_rate"]
    margin_gap = oracle["mean_margin"] - baseline["mean_margin"]
    return {
        "oracle_score_gap_pp": 100 * score_gap,
        "score_uplift_pp": 100 * (policy["family_equal_score_rate"] - baseline["family_equal_score_rate"]),
        "score_gap_recovered": None if abs(score_gap) < 1e-12 else (policy["family_equal_score_rate"] - baseline["family_equal_score_rate"]) / score_gap,
        "oracle_margin_gap": margin_gap,
        "margin_uplift": policy["mean_margin"] - baseline["mean_margin"],
        "margin_gap_recovered": None if abs(margin_gap) < 1e-12 else (policy["mean_margin"] - baseline["mean_margin"]) / margin_gap,
    }


def greedy_expand(dev: list[dict], all_ids: list[str], size: int) -> list[str]:
    selected = list(V17_IDS)
    while len(selected) < size:
        choices = []
        for rid in all_ids:
            if rid in selected:
                continue
            metric = summarize(oracle_rows(dev, selected + [rid]))
            choices.append((metric["family_equal_score_rate"], metric["worst_family_score_rate"], metric["mean_margin"], rid))
        selected.append(max(choices)[-1])
    return selected


def evaluate_subset(dev: list[dict], test: list[dict], subset: list[str], label: str) -> dict:
    single = best_single(dev, subset)
    baseline = summarize([row for row in test if row["route"] == single])
    oracle = summarize(oracle_rows(test, subset))
    first = train_lookup(dev, subset, ("shop72",))
    first_test = summarize(apply_lookup(test, subset, first))
    pair = train_lookup(dev, subset, ("shop_pair",), fallback=first)
    pair_test = summarize(apply_lookup(test, subset, pair))
    s72 = train_public_stump(dev, subset, 72, first)
    s72_test = summarize(apply_public_stump(test, subset, s72))
    s120 = train_public_stump(dev, subset, 120, first)
    s120_test = summarize(apply_public_stump(test, subset, s120))
    return {
        "label": label, "routes": subset, "best_single": single,
        "test": {
            "best_single": baseline,
            "unattainable_per_game_oracle": oracle,
            "first_shop_step72": {**first_test, "recovery": recovery(first_test, baseline, oracle)},
            "first_two_shops_step144_future_information": {**pair_test, "recovery": recovery(pair_test, baseline, oracle)},
            "public_state_step72_one_stump": {
                **s72_test, "feature": s72["feature"], "threshold": s72["threshold"],
                "recovery": recovery(s72_test, baseline, oracle),
            },
            "public_state_step120_future_information_one_stump": {
                **s120_test, "feature": s120["feature"], "threshold": s120["threshold"],
                "recovery": recovery(s120_test, baseline, oracle),
            },
        },
        "trained_first_shop_mapping": {"|".join(key): value for key, value in first["choices"].items()},
        "trained_first_two_mapping": {"|".join(key): value for key, value in pair["choices"].items()},
        "development_only_stump_selection": {
            "step72": {"feature": s72["feature"], "threshold": s72["threshold"], "metric": s72["dev"]},
            "step120": {"feature": s120["feature"], "threshold": s120["threshold"], "metric": s120["dev"]},
        },
    }


def main() -> int:
    routes = candidate_routes()
    ids = [row["id"] for row in routes]
    dev72 = run_table(routes, DEV_PROXIES, DEV_SEEDS, "dev", 72)
    test72 = run_table(routes, TEST_PROXIES, TEST_SEEDS, "heldout", 72)
    dev144 = run_table(routes, DEV_PROXIES, DEV_SEEDS, "dev", 144)
    test144 = run_table(routes, TEST_PROXIES, TEST_SEEDS, "heldout", 144)

    subsets = {
        "v17_two_routes": list(V17_IDS),
        "greedy_three_routes": greedy_expand(dev72, ids, 3),
        "greedy_five_routes": greedy_expand(dev72, ids, 5),
    }
    branch72 = {name: evaluate_subset(dev72, test72, subset, name) for name, subset in subsets.items()}
    # For the delay counterfactual, subset selection stays frozen from the day-3
    # development table.  It is not re-optimized on delayed outcomes.
    branch144 = {name: evaluate_subset(dev144, test144, subset, name) for name, subset in subsets.items()}

    v17 = list(V17_IDS)
    current_rows = []
    for group in game_groups(test72, v17).values():
        shop = group[0]["shop72"]
        rid = V17_IDS[1] if shop == "YARN_STORE" else V17_IDS[0]
        current_rows.append(next(row for row in group if row["route"] == rid))
    current = summarize(current_rows)
    delayed_pair = branch144["v17_two_routes"]["test"]["first_two_shops_step144_future_information"]

    result = {
        "status": "CAUSAL_INFORMATION_VALUE_FIXED_STREAM_UPPER_BOUND",
        "engine": str(KAGSIM.ENGINE_VERSION),
        "frozen_design": {
            "candidate_route_source_date": "2026-08-25",
            "development_proxy_dates": sorted({x[0] for x in DEV_PROXIES}),
            "heldout_proxy_dates": sorted({x[0] for x in TEST_PROXIES}),
            "development_seed_range": [DEV_SEEDS.start, DEV_SEEDS.stop - 1],
            "heldout_seed_range": [TEST_SEEDS.start, TEST_SEEDS.stop - 1],
            "both_seats": True,
            "development_proxy_families": len(DEV_PROXIES),
            "heldout_proxy_families": len(TEST_PROXIES),
            "route_candidates": len(routes),
            "no_heldout_date_or_seed_used_for_route_subset_or_mapping_or_stump_selection": True,
        },
        "interpretation_contract": {
            "branch72": "route is selected at day 3; first-shop and step72 public-state features are causal and executable",
            "post72_features": "first-two-shop and step120 features predict branch72 outcomes but are unavailable at day3; informational upper bounds only",
            "branch144": "shared default prefix is retained until day6, then replay tails branch; estimates delay opportunity cost but tail state compatibility is not production-certified",
            "per_game_oracle": "uses final reward and is unattainable; diversity ceiling only",
            "fixed_stream": "replay action streams do not adapt to the counterfactual game; no Kaggle gold claim",
        },
        "selected_subsets_development_only": subsets,
        "branch_at_step72": branch72,
        "branch_at_step144_delay_counterfactual": branch144,
        "current_v17_frozen_mapping_heldout": current,
        "delay_decision": {
            "current_day3_v17_score_rate": current["family_equal_score_rate"],
            "current_day3_v17_mean_margin": current["mean_margin"],
            "day6_two_shop_best_learned_score_rate": delayed_pair["family_equal_score_rate"],
            "day6_two_shop_best_learned_mean_margin": delayed_pair["mean_margin"],
            "day6_minus_current_score_pp": 100 * (delayed_pair["family_equal_score_rate"] - current["family_equal_score_rate"]),
            "day6_minus_current_margin": delayed_pair["mean_margin"] - current["mean_margin"],
        },
        "candidate_routes": [{key: row[key] for key in ("id", "team", "episode", "behavior_sha256")} for row in routes],
    }
    (HERE / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "subsets": subsets,
        "v17_branch72": branch72["v17_two_routes"]["test"],
        "delay": result["delay_decision"],
        "three_first": branch72["greedy_three_routes"]["test"]["first_shop_step72"],
        "five_first": branch72["greedy_five_routes"]["test"]["first_shop_step72"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
