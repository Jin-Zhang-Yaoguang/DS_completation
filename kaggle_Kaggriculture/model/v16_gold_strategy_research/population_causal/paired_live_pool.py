#!/usr/bin/env python3
"""Paired L1 development evaluation over the exposed 2026-08-25 seed panel.

This is deliberately not a formal evaluator.  It reconstructs a candidate and
its A2 baseline against the same live opponent, seed, and seat.  Every policy
instance is freshly imported for every game because the historical agents keep
episode state in module globals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable


REPO = Path(__file__).resolve().parents[4]
MODEL = REPO / "kaggle_Kaggriculture" / "model"
CPPSIM = (
    MODEL
    / "community_research"
    / "2026-08-26"
    / "live_cli"
    / "external_repos"
    / "kaggriculture-cppsim"
)
AGENT_FACTORY = MODEL / "v10_replay_lolo_router"
Kaito_SHA256 = "dadee25a9840313218384208c53b2c4752f82c3209cc654632e0b96c65e2664a"
SEEDS = (
    41009357,
    76771668,
    313115237,
    496071140,
    569547387,
    870316931,
    1245824168,
    1456608927,
    1460201458,
    1551885668,
    1568863178,
    1729483625,
    1762962646,
    2068071795,
    2095823972,
)
MODEL_PATHS = {
    "a2": MODEL / "v12a2_no_shop_gate" / "main.py",
    "v13c": MODEL / "v13c_a2_v8_no_wool_throttle" / "main.py",
    "v1_adaptive": MODEL / "v1_adaptive_market" / "main.py",
    "v3_bc_ppo": MODEL / "v3_bc_ppo_hybrid" / "main.py",
    "v9_anti_mirror": MODEL / "v9_anti_mirror" / "main.py",
    "r002_fixed": MODEL / "v12_incumbent_r002" / "main.py",
    "v5_ppo_topdays": MODEL / "v5_ppo_v2_league" / "v5_ppo_v2_topdays" / "main.py",
    "v5_rule": MODEL / "v5_rule_hybrid" / "main.py",
}
HISTORICAL_OPPONENTS = (
    "v1_adaptive",
    "v3_bc_ppo",
    "v9_anti_mirror",
    "r002_fixed",
    "v5_ppo_topdays",
    "v5_rule",
)


def load_runtime() -> tuple[Any, Any, Any]:
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError(f"cppsim extension is not built under {CPPSIM / 'build'}")
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(builds[-1]))
    sys.path.insert(0, str(AGENT_FACTORY))
    import kagsim  # type: ignore
    from agent_factory import Registry, create_agent  # type: ignore

    if str(kagsim.ENGINE_VERSION) != "1.32.7":
        raise RuntimeError(f"expected engine 1.32.7, got {kagsim.ENGINE_VERSION}")
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    return kagsim, registry, create_agent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_paths(kaito_main: Path) -> dict[str, Path]:
    if not kaito_main.is_file():
        raise FileNotFoundError(kaito_main)
    actual = sha256(kaito_main)
    if actual != Kaito_SHA256:
        raise RuntimeError(f"Kaito main.py SHA mismatch: expected {Kaito_SHA256}, got {actual}")
    paths = dict(MODEL_PATHS)
    paths["kaito_v48"] = kaito_main.resolve()
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing policy source(s): {missing}")
    return paths


def fresh_agent(model_id: str, paths: dict[str, Path], registry: Any, create_agent: Any) -> Any:
    return create_agent(
        registry,
        {
            "id": model_id,
            "kind": "python",
            "path": str(paths[model_id]),
            "entrypoint": "agent",
        },
    )


def play(
    policy_id: str,
    opponent_id: str,
    seed: int,
    policy_seat: int,
    paths: dict[str, Path],
    kagsim: Any,
    registry: Any,
    create_agent: Any,
) -> tuple[float, float]:
    policy = fresh_agent(policy_id, paths, registry, create_agent)
    opponent = fresh_agent(opponent_id, paths, registry, create_agent)
    agents = [None, None]
    agents[policy_seat] = policy
    agents[1 - policy_seat] = opponent
    game = kagsim.Game(int(seed))
    while not game.done:
        game.step(agents[0](game.observe(0)), agents[1](game.observe(1)))
    rewards = (float(game.reward(0)), float(game.reward(1)))
    return rewards[policy_seat], rewards[1 - policy_seat]


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def quantile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("cannot take a quantile of an empty sequence")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "comparisons": len(rows),
        "baseline_score_rate": statistics.mean(row["baseline_score"] for row in rows),
        "candidate_score_rate": statistics.mean(row["candidate_score"] for row in rows),
        "score_uplift_pp": 100.0 * statistics.mean(row["score_delta"] for row in rows),
        "score_positive_zero_negative": [
            sum(row["score_delta"] > 0 for row in rows),
            sum(row["score_delta"] == 0 for row in rows),
            sum(row["score_delta"] < 0 for row in rows),
        ],
        "margin_delta_mean": statistics.mean(row["margin_delta"] for row in rows),
        "margin_delta_median": statistics.median(row["margin_delta"] for row in rows),
        "margin_positive_zero_negative": [
            sum(row["margin_delta"] > 0 for row in rows),
            sum(row["margin_delta"] == 0 for row in rows),
            sum(row["margin_delta"] < 0 for row in rows),
        ],
        "own_delta_mean": statistics.mean(row["own_delta"] for row in rows),
        "w_to_l": sum(row["baseline_score"] == 1.0 and row["candidate_score"] == 0.0 for row in rows),
        "l_to_w": sum(row["baseline_score"] == 0.0 and row["candidate_score"] == 1.0 for row in rows),
    }


def bootstrap(rows: list[dict[str, Any]], seeds: list[int], reps: int, rng_seed: int) -> dict[str, list[float]]:
    by_seed = {seed: [row for row in rows if int(row["seed"]) == seed] for seed in seeds}
    rng = random.Random(rng_seed)
    samples: list[tuple[float, float, float, float]] = []
    for _ in range(reps):
        sampled = rng.choices(seeds, k=len(seeds))
        selected = [row for seed in sampled for row in by_seed[seed]]
        samples.append(
            (
                statistics.mean(row["baseline_score"] for row in selected),
                statistics.mean(row["candidate_score"] for row in selected),
                statistics.mean(row["score_delta"] for row in selected),
                statistics.mean(row["margin_delta"] for row in selected),
            )
        )
    names = ("baseline_score_rate", "candidate_score_rate", "score_uplift", "margin_uplift")
    return {
        name: [quantile((sample[index] for sample in samples), 0.025), quantile((sample[index] for sample in samples), 0.975)]
        for index, name in enumerate(names)
    }


def build_result(
    experiment: str,
    rows: list[dict[str, Any]],
    seeds: list[int],
    opponents: list[str],
    reps: int,
    rng_seed: int,
) -> dict[str, Any]:
    candidate = "v13c" if experiment == "v13c" else "kaito_v48"
    status = "DEVELOPMENT_EXPOSED_2026_08_25_SEEDS_NOT_FORMAL"
    result: dict[str, Any] = {
        "status": status,
        "decision": "REJECT" if experiment == "v13c" else "HOLD",
        "engine": "1.32.7",
        "policies": {"baseline": "a2", "candidate": candidate},
        "kaito": {
            "main_sha256": Kaito_SHA256,
            "license_verified": False,
            "source_vendored": False,
        },
        "seed_source": "15 version-aware deterministic seeds from the exposed 2026-08-25 replay panel",
        "seeds": seeds,
        "opponents": opponents,
        "bootstrap": {"unit": "environment_seed", "reps": reps, "rng": "python.random.Random", "rng_seed": rng_seed},
        "overall": summarize(rows),
        "by_opponent": {opponent: summarize([row for row in rows if row["opponent"] == opponent]) for opponent in opponents},
        "source_cluster_bootstrap_ci95": bootstrap(rows, seeds, reps, rng_seed),
        "rows": rows,
    }
    return result


def run_experiment(
    experiment: str,
    kaito_main: Path,
    seed_limit: int | None,
    opponent_limit: int | None,
    reps: int,
    rng_seed: int,
) -> dict[str, Any]:
    kagsim, registry, create_agent = load_runtime()
    paths = model_paths(kaito_main)
    seeds = list(SEEDS[:seed_limit] if seed_limit else SEEDS)
    opponents = list(((*HISTORICAL_OPPONENTS, "kaito_v48") if experiment == "v13c" else HISTORICAL_OPPONENTS))
    if opponent_limit:
        opponents = opponents[:opponent_limit]
    candidate = "v13c" if experiment == "v13c" else "kaito_v48"
    rows: list[dict[str, Any]] = []
    for opponent in opponents:
        for seed in seeds:
            for seat in (0, 1):
                baseline_own, baseline_opp = play("a2", opponent, seed, seat, paths, kagsim, registry, create_agent)
                candidate_own, candidate_opp = play(candidate, opponent, seed, seat, paths, kagsim, registry, create_agent)
                baseline_margin = baseline_own - baseline_opp
                candidate_margin = candidate_own - candidate_opp
                baseline_score = score(baseline_margin)
                candidate_score = score(candidate_margin)
                rows.append(
                    {
                        "opponent": opponent,
                        "seed": seed,
                        "seat": seat,
                        "score_delta": candidate_score - baseline_score,
                        "margin_delta": candidate_margin - baseline_margin,
                        "own_delta": candidate_own - baseline_own,
                        "opponent_delta": candidate_opp - baseline_opp,
                        "baseline_score": baseline_score,
                        "candidate_score": candidate_score,
                        "baseline_margin": baseline_margin,
                        "candidate_margin": candidate_margin,
                    }
                )
    return build_result(experiment, rows, seeds, opponents, reps, rng_seed)


def verify_rows(actual: dict[str, Any], expected_path: Path) -> None:
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    keys = ("score_delta", "margin_delta", "baseline_score", "candidate_score", "baseline_margin", "candidate_margin")
    index = {(row["opponent"], int(row["seed"]), int(row["seat"])): row for row in expected["rows"]}
    for row in actual["rows"]:
        identity = (row["opponent"], int(row["seed"]), int(row["seat"]))
        reference = index.get(identity)
        if reference is None:
            raise AssertionError(f"row absent from frozen result: {identity}")
        for key in keys:
            if float(row[key]) != float(reference[key]):
                raise AssertionError(f"{identity} {key}: actual={row[key]}, expected={reference[key]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", choices=("v13c", "kaito", "all"), default="all")
    parser.add_argument("--kaito-main", type=Path, required=True, help="external Kaito v48 main.py; SHA is enforced")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("results"))
    parser.add_argument("--seed-limit", type=int)
    parser.add_argument("--opponent-limit", type=int)
    parser.add_argument("--bootstrap-reps", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20_260_826)
    parser.add_argument("--verify-against", type=Path, help="compare regenerated row metrics with a frozen result")
    args = parser.parse_args()
    experiments = ("v13c", "kaito") if args.experiment == "all" else (args.experiment,)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for experiment in experiments:
        result = run_experiment(
            experiment,
            args.kaito_main,
            args.seed_limit,
            args.opponent_limit,
            args.bootstrap_reps,
            args.bootstrap_seed,
        )
        if args.verify_against:
            verify_rows(result, args.verify_against)
            result["verification"] = {"frozen_rows_exact": True, "frozen_path": str(args.verify_against)}
        filename = "v13c_vs_a2_paired_dev.json" if experiment == "v13c" else "kaito_v48_vs_a2_paired_dev.json"
        output = args.output_dir / filename
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(output), "overall": result["overall"], "verification": result.get("verification")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
