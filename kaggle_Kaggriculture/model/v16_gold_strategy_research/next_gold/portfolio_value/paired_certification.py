#!/usr/bin/env python3
"""Paired uncertainty audit for the frozen two-route information-value result."""

from __future__ import annotations

import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

import analyze_information_value as a


HERE = Path(__file__).resolve().parent


def indexed(rows, subset):
    return {
        (row["family"], row["seed"], row["seat"]): row
        for row in rows if row["route"] in subset
    }


def select_lookup(rows, subset, model):
    picked = a.apply_lookup(rows, subset, model)
    return {(row["family"], row["seed"], row["seat"]): row for row in picked}


def select_stump(rows, subset, model):
    picked = a.apply_public_stump(rows, subset, model)
    return {(row["family"], row["seed"], row["seat"]): row for row in picked}


def bootstrap(values: dict[tuple, float], draws=10000):
    blocks = defaultdict(list)
    for (family, seed, _seat), value in values.items():
        blocks[(family, seed)].append(value)
    means = [statistics.mean(v) for v in blocks.values()]
    rng = random.Random(20260826)
    samples = []
    for _ in range(draws):
        samples.append(statistics.mean(rng.choice(means) for _ in means))
    samples.sort()
    return [samples[int(0.025 * draws)], samples[int(0.975 * draws)]]


def paired(candidate, baseline):
    score_delta, margin_delta = {}, {}
    by_family = defaultdict(list)
    for key, row in candidate.items():
        base = baseline[key]
        score_delta[key] = row["game_score"] - base["game_score"]
        margin_delta[key] = row["margin"] - base["margin"]
        by_family[key[0]].append((score_delta[key], margin_delta[key]))
    return {
        "games": len(candidate),
        "score_delta_pp": 100 * statistics.mean(score_delta.values()),
        "score_delta_cluster95_pp": [100 * x for x in bootstrap(score_delta)],
        "margin_delta": statistics.mean(margin_delta.values()),
        "margin_delta_cluster95": bootstrap(margin_delta),
        "positive_zero_negative_score": [
            sum(x > 0 for x in score_delta.values()),
            sum(x == 0 for x in score_delta.values()),
            sum(x < 0 for x in score_delta.values()),
        ],
        "by_family": {
            family: {
                "score_delta_pp": 100 * statistics.mean(x[0] for x in values),
                "margin_delta": statistics.mean(x[1] for x in values),
            }
            for family, values in by_family.items()
        },
    }


def main():
    routes = [row for row in a.candidate_routes() if row["id"] in a.V17_IDS]
    subset = list(a.V17_IDS)
    dev72 = a.run_table(routes, a.DEV_PROXIES, a.DEV_SEEDS, "dev", 72)
    test72 = a.run_table(routes, a.TEST_PROXIES, a.TEST_SEEDS, "heldout", 72)
    dev144 = a.run_table(routes, a.DEV_PROXIES, a.DEV_SEEDS, "dev", 144)
    test144 = a.run_table(routes, a.TEST_PROXIES, a.TEST_SEEDS, "heldout", 144)

    single_id = a.best_single(dev72, subset)
    baseline = {
        (row["family"], row["seed"], row["seat"]): row
        for row in test72 if row["route"] == single_id
    }
    first = a.train_lookup(dev72, subset, ("shop72",))
    pair = a.train_lookup(dev72, subset, ("shop_pair",), fallback=first)
    state72 = a.train_public_stump(dev72, subset, 72, first)
    state120 = a.train_public_stump(dev72, subset, 120, first)

    current = select_lookup(test72, subset, first)
    candidates = {
        "day3_first_shop_vs_single": (current, baseline),
        "day3_first_two_future_info_vs_single": (select_lookup(test72, subset, pair), baseline),
        "day3_public72_stump_vs_first_shop": (select_stump(test72, subset, state72), current),
        "day3_public120_future_stump_vs_first_shop": (select_stump(test72, subset, state120), current),
    }
    # Day-6 model is trained only on dev day-6 outcomes, while its route subset
    # stays frozen.  Compare it directly with the executable day-3 mapping.
    delayed_first = a.train_lookup(dev144, subset, ("shop72",))
    delayed_pair = a.train_lookup(dev144, subset, ("shop_pair",), fallback=delayed_first)
    candidates["day6_two_shop_vs_current_day3"] = (select_lookup(test144, subset, delayed_pair), current)

    result = {
        "status": "PAIRED_CLUSTER_BOOTSTRAP_HELDOUT_ONLY",
        "cluster": "opponent_family x seed; both seats stay together",
        "draws": 10000,
        "heldout_dates": sorted({x[0] for x in a.TEST_PROXIES}),
        "heldout_seeds": [a.TEST_SEEDS.start, a.TEST_SEEDS.stop - 1],
        "comparisons": {name: paired(candidate, base) for name, (candidate, base) in candidates.items()},
    }
    (HERE / "paired_certification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
