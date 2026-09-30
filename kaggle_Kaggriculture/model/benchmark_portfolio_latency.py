#!/usr/bin/env python3
"""Benchmark frozen V77-V81 serving latency against the V76 parent."""

from __future__ import annotations

import json
import os
from pathlib import Path
import statistics
import sys
import time


HERE = Path(__file__).resolve().parent
CPPSIM = HERE / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = HERE / "v10_replay_lolo_router"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore


POLICIES = {
    "v76_adjacent_safe_buy_lead": HERE / "v76_adjacent_safe_buy_lead/main.py",
    "v77_demand_contract_moe": HERE / "v77_demand_contract_moe/main.py",
    "v78_opponent_belief_moe": HERE / "v78_opponent_belief_moe/main.py",
    "v79_cashflow_tail_risk_moe": HERE / "v79_cashflow_tail_risk_moe/main.py",
    "v80_spatial_work_stealing_moe": HERE / "v80_spatial_work_stealing_moe/main.py",
    "v81_shared_market_product_mpc": HERE / "v81_shared_market_product_mpc/main.py",
}
OPPONENT = HERE / "v21_top_meta_moe/main.py"
SEEDS = (82001, 82002)


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    index = (len(values) - 1) * p
    low = int(index)
    high = min(len(values) - 1, low + 1)
    weight = index - low
    return values[low] * (1.0 - weight) + values[high] * weight


def benchmark(model_id: str, path: Path) -> dict[str, object]:
    elapsed_ms: list[float] = []
    completed = 0
    for seed in SEEDS:
        for seat in (0, 1):
            registry = Registry(path=HERE / "latency_registry.json", models={}, raw={})
            own = create_agent(registry, {
                "id": f"{model_id}_{seed}_{seat}_{os.getpid()}",
                "kind": "python", "path": str(path), "entrypoint": "agent",
            })
            rival = create_agent(registry, {
                "id": f"opponent_{model_id}_{seed}_{seat}_{os.getpid()}",
                "kind": "python", "path": str(OPPONENT), "entrypoint": "agent",
            })
            agents = [None, None]
            agents[seat], agents[1 - seat] = own, rival
            game = kagsim.Game(seed)
            while not game.done:
                observations = [game.observe(0), game.observe(1)]
                started = time.perf_counter_ns()
                own_action = agents[seat](observations[seat])
                elapsed_ms.append((time.perf_counter_ns() - started) / 1_000_000)
                rival_action = agents[1 - seat](observations[1 - seat])
                actions = [None, None]
                actions[seat], actions[1 - seat] = own_action, rival_action
                game.step(actions[0], actions[1])
            completed += 1
    return {
        "games": completed,
        "calls": len(elapsed_ms),
        "mean_ms": statistics.mean(elapsed_ms),
        "p99_ms": percentile(elapsed_ms, 0.99),
        "max_ms": max(elapsed_ms),
    }


def main() -> None:
    models = {model_id: benchmark(model_id, path) for model_id, path in POLICIES.items()}
    parent_p99 = float(models["v76_adjacent_safe_buy_lead"]["p99_ms"])
    for model_id, row in models.items():
        row["p99_vs_parent"] = float(row["p99_ms"]) / parent_p99
        row["gate_p99_below_250ms"] = float(row["p99_ms"]) < 250.0
        row["gate_p99_at_most_1_25x_parent"] = model_id == "v76_adjacent_safe_buy_lead" or row["p99_vs_parent"] <= 1.25
    result = {
        "schema": "kaggriculture-portfolio-latency-qa-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "seeds": list(SEEDS),
        "seats": [0, 1],
        "opponent": "v21_top_meta_moe",
        "models": models,
    }
    result["gate"] = "PASS" if all(
        row["gate_p99_below_250ms"] and row["gate_p99_at_most_1_25x_parent"]
        for model_id, row in models.items() if model_id != "v76_adjacent_safe_buy_lead"
    ) else "FAIL"
    output = HERE / "portfolio_latency_qa_20260829.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
