#!/usr/bin/env python3
"""Independent completeness and calculation checks for the V22-V29 rematch."""

from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
MODEL = PROJECT / "model"
CANDIDATES = {
    "v22": MODEL / "v22_lucaskna_no_delay_ablation" / "main.py",
    "v23": MODEL / "v23_demand_fraction_search" / "main.py",
    "v24": MODEL / "v24_shop_expert_router" / "main.py",
    "v25": MODEL / "v25_prefix_compatible_experts" / "main.py",
    "v26": MODEL / "v26_step72_milan_router" / "main.py",
    "v27": MODEL / "v27_lucaskna_shop_router" / "main.py",
    "v28": MODEL / "v28_broad_smoothie_router" / "main.py",
    "v29": MODEL / "v29_champion_selection" / "main.py",
}


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def quantile(values: list[float], p: float) -> float:
    values = sorted(values)
    x = (len(values) - 1) * p
    low, high = math.floor(x), math.ceil(x)
    return values[low] if low == high else values[low] * (high - x) + values[high] * (x - low)


def bootstrap_ci(seed_values: dict[int, float], rng_seed: int, draws: int = 20000) -> list[float]:
    seeds = list(seed_values)
    rng = random.Random(rng_seed)
    samples = [statistics.mean(seed_values[seed] for seed in rng.choices(seeds, k=len(seeds))) for _ in range(draws)]
    return [quantile(samples, 0.025), quantile(samples, 0.975)]


def main() -> int:
    result = json.loads((HERE / "rematch_results.json").read_text())
    manifest = result["manifest"]
    rows = result["rows"]
    expected_seeds = set(range(manifest["seed_range"][0], manifest["seed_range"][1] + 1))
    keys = [(row["candidate"], row["opponent"], row["seed"], row["seat"]) for row in rows]
    checks = {
        "row_count": len(rows) == manifest["total_games"] == 10240,
        "unique_job_keys": len(set(keys)) == len(keys),
        "finite_rewards": all(math.isfinite(row["own"]) and math.isfinite(row["opponent_reward"]) for row in rows),
        "margin_identity": all(row["margin"] == row["own"] - row["opponent_reward"] for row in rows),
        "candidate_coverage": all(sum(row["candidate"] == candidate for row in rows) == 1280 for candidate in manifest["candidates"]),
        "pair_coverage": all(sum(row["candidate"] == candidate and row["opponent"] == opponent for row in rows) == 256 for candidate in manifest["candidates"] for opponent in manifest["opponents"]),
        "seed_coverage": all({row["seed"] for row in rows if row["candidate"] == candidate and row["opponent"] == opponent} == expected_seeds for candidate in manifest["candidates"] for opponent in manifest["opponents"]),
        "seat_coverage": all({row["seat"] for row in rows if row["candidate"] == candidate and row["opponent"] == opponent and row["seed"] == seed} == {0, 1} for candidate in manifest["candidates"] for opponent in manifest["opponents"] for seed in expected_seeds),
        "source_hashes_current": all(hashlib.sha256(path.read_bytes()).hexdigest() == result["source_sha256"][candidate] for candidate, path in CANDIDATES.items()),
    }
    recomputed = {}
    alternate_ci = {}
    tail_risk = {}
    baseline = {(row["opponent"], row["seed"], row["seat"]): row for row in rows if row["candidate"] == "v29"}
    comparisons = {}
    for index, candidate in enumerate(manifest["candidates"]):
        selected = [row for row in rows if row["candidate"] == candidate]
        wins = sum(row["margin"] > 0 for row in selected)
        ties = sum(row["margin"] == 0 for row in selected)
        losses = sum(row["margin"] < 0 for row in selected)
        recomputed[candidate] = {
            "wins_ties_losses": [wins, ties, losses],
            "score_rate": (wins + 0.5 * ties) / len(selected),
            "mean_margin": statistics.mean(row["margin"] for row in selected),
        }
        by_seed = defaultdict(list)
        for row in selected:
            by_seed[row["seed"]].append(score(row["margin"]))
        alternate_ci[candidate] = bootstrap_ci({seed: statistics.mean(values) for seed, values in by_seed.items()}, 20260828 + index)
        margins = [row["margin"] for row in selected]
        tail_risk[candidate] = {
            "margin_p05": quantile(margins, 0.05), "margin_p10": quantile(margins, 0.10),
            "margin_median": quantile(margins, 0.50), "catastrophic_loss_below_minus_10000": sum(value < -10000 for value in margins),
        }
        if candidate != "v29":
            deltas = []
            for row in selected:
                prior = baseline[(row["opponent"], row["seed"], row["seat"])]
                deltas.append((row["seed"], score(row["margin"]) - score(prior["margin"])))
            by_seed_delta = defaultdict(list)
            for seed, delta in deltas:
                by_seed_delta[seed].append(delta)
            comparisons[candidate] = {
                "score_uplift_pp": 100 * statistics.mean(delta for _, delta in deltas),
                "alternate_ci95_pp": [100 * value for value in bootstrap_ci({seed: statistics.mean(values) for seed, values in by_seed_delta.items()}, 20261828 + index)],
            }
    checks["stored_aggregates_match"] = all(
        recomputed[candidate]["wins_ties_losses"] == result["absolute"][candidate]["wins_ties_losses"]
        and recomputed[candidate]["score_rate"] == result["absolute"][candidate]["score_rate"]
        and recomputed[candidate]["mean_margin"] == result["absolute"][candidate]["mean_margin"]
        for candidate in manifest["candidates"]
    )
    v27 = {(row["opponent"], row["seed"], row["seat"]): (row["own"], row["opponent_reward"], row["margin"]) for row in rows if row["candidate"] == "v27"}
    v28 = {(row["opponent"], row["seed"], row["seat"]): (row["own"], row["opponent_reward"], row["margin"]) for row in rows if row["candidate"] == "v28"}
    checks["v27_v28_exact_outcome_equivalence"] = v27 == v28
    checks["v29_is_v21_source_plus_version_only"] = CANDIDATES["v29"].read_bytes().startswith((MODEL / "v21_top_meta_moe" / "main.py").read_bytes())
    validation = {
        "schema": "kaggriculture-v22-through-v29-rematch-validation-v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks, "recomputed": recomputed, "alternate_score_rate_ci95": alternate_ci,
        "alternate_paired_vs_v29": comparisons, "tail_risk": tail_risk,
    }
    (HERE / "validation_results.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
