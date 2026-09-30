#!/usr/bin/env python3
"""串行基准 V10 ShadowRouter 与 V11 FastShadowRouter 的整局延迟。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import time
from typing import Any, Sequence

try:
    from .fast_router import create_agent as create_fast_router
    from .league import HERE, _atomic_json
    from .verify_fast_router import _run
except ImportError:
    from league import HERE, _atomic_json
    from fast_router import create_agent as create_fast_router
    from verify_fast_router import _run

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import load_registry
from kaggle_Kaggriculture.model.v10_replay_lolo_router.router import create_router


DEFAULT_EXPERTS = ("baseline_v1", "baseline_v2", "baseline_v5", "baseline_v8")


def _router_spec(experts: Sequence[str]) -> dict[str, Any]:
    experts = [str(item) for item in experts]
    return {
        "id": "fast_latency_probe",
        "kind": "router",
        "router_kind": "rule",
        "experts": experts,
        "anchor": experts[0],
        "switch_step": 72,
        "rule": {
            "low_cash": 0.0,
            "novelty_distance": 4.0,
            "default_priority": [experts[0]],
            "survival_priority": [experts[1], experts[0]],
            "yarn_priority": [experts[-1], experts[0]],
            "novel_priority": [experts[0]],
        },
    }


def benchmark(
    registry_path: Path,
    seeds: Sequence[int],
    warmup_seed: int,
    output_path: Path,
    experts: Sequence[str] = DEFAULT_EXPERTS,
    opponent_id: str = "baseline_v1",
) -> dict[str, Any]:
    if not (3 <= len(set(int(item) for item in seeds)) <= 6):
        raise ValueError("latency benchmark requires 3-6 unique timed seeds")
    registry = load_registry(registry_path)
    experts = [str(item) for item in experts]
    spec = _router_spec(experts)
    embedded = {model_id: registry.require(model_id) for model_id in experts}

    def original_factory():
        return create_router(registry, spec)

    def fast_factory():
        return create_fast_router(spec, embedded, str(registry.path.parent))

    # Same-machine serial warmup. Warmup output is intentionally discarded.
    _run(registry, original_factory, opponent_id, int(warmup_seed), 0)
    _run(registry, fast_factory, opponent_id, int(warmup_seed), 0)

    timings = {"original": [], "fast": []}
    rows = []
    jobs = [(int(seed), seat) for seed in seeds for seat in (0, 1)]
    for index, (seed, seat) in enumerate(jobs):
        # Alternate order to avoid systematically granting one implementation
        # the warmer filesystem/cache state.
        order = ("original", "fast") if index % 2 == 0 else ("fast", "original")
        local = {}
        outputs = {}
        for name in order:
            factory = original_factory if name == "original" else fast_factory
            started = time.perf_counter()
            outputs[name] = _run(registry, factory, opponent_id, seed, seat)
            elapsed = time.perf_counter() - started
            timings[name].append(elapsed)
            local[name] = elapsed
        rows.append(
            {
                "seed": seed,
                "router_seat": seat,
                "execution_order": list(order),
                "original_seconds": local["original"],
                "fast_seconds": local["fast"],
                "speedup": local["original"] / local["fast"],
                "action_equal": outputs["original"]["actions"] == outputs["fast"]["actions"],
                "reward_equal": outputs["original"]["rewards"] == outputs["fast"]["rewards"],
                "status_equal": outputs["original"]["statuses"] == outputs["fast"]["statuses"],
                "selection_equal": outputs["original"]["selected"] == outputs["fast"]["selected"],
            }
        )
    original_mean = statistics.fmean(timings["original"])
    fast_mean = statistics.fmean(timings["fast"])
    original_median = statistics.median(timings["original"])
    fast_median = statistics.median(timings["fast"])
    report = {
        "schema": "kaggriculture-v11-fast-router-latency-1",
        "method": "same_machine_serial_warmup_then_alternating_order",
        "registry": str(registry.path),
        "warmup_seed": int(warmup_seed),
        "timed_seeds": [int(item) for item in seeds],
        "seats": [0, 1],
        "games_per_implementation": len(jobs),
        "all_equivalent": all(
            row["action_equal"]
            and row["reward_equal"]
            and row["status_equal"]
            and row["selection_equal"]
            for row in rows
        ),
        "original": {
            "mean_seconds": original_mean,
            "median_seconds": original_median,
            "min_seconds": min(timings["original"]),
            "max_seconds": max(timings["original"]),
        },
        "fast": {
            "mean_seconds": fast_mean,
            "median_seconds": fast_median,
            "min_seconds": min(timings["fast"]),
            "max_seconds": max(timings["fast"]),
        },
        "speedup": {
            "mean_ratio": original_mean / fast_mean,
            "median_ratio": original_median / fast_median,
        },
        "rows": rows,
    }
    _atomic_json(output_path, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    parser.add_argument("--warmup-seed", type=int, required=True)
    parser.add_argument("--experts", nargs="+", default=list(DEFAULT_EXPERTS))
    parser.add_argument("--opponent", default="baseline_v1")
    parser.add_argument("--output", type=Path, default=HERE / "fast_router_latency.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = benchmark(
        args.registry,
        args.seeds,
        args.warmup_seed,
        args.output,
        args.experts,
        args.opponent,
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "games_per_implementation": report["games_per_implementation"],
                "all_equivalent": report["all_equivalent"],
                "mean_speedup": report["speedup"]["mean_ratio"],
                "median_speedup": report["speedup"]["median_ratio"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["all_equivalent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

