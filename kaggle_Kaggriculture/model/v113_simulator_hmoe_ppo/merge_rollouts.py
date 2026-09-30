"""Merge parallel V113 rollout shards and normalize advantages globally."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    shards = []
    reports = []
    for path in args.input:
        with np.load(path) as archive:
            shards.append({key: archive[key] for key in archive.files})
        reports.append(json.loads(path.with_suffix(".json").read_text(encoding="utf-8")))
    contract_keys = (
        "worker_temperature", "gamma", "lambda_gae", "potential",
        "terminal_mode", "margin_scale", "opponent_impact_weight",
        "cash_floor", "cash_reserve_weight", "cash_shortfall_weight",
        "market_inventory_reference", "market_inventory_scale",
        "market_liquidity_weight", "market_cash_weight",
        "terminal_catastrophe_weight", "terminal_own_log_weight",
        "training_step_start", "training_step_end", "phase_only",
        "phase_include_terminal_objective", "ignore_value_baseline",
    )
    contract = {key: reports[0].get(key) for key in contract_keys}
    for report in reports[1:]:
        observed = {key: report.get(key) for key in contract_keys}
        if observed != contract:
            raise ValueError(
                f"rollout shards have different collection contracts: {contract} != {observed}"
            )
    keys = set(shards[0])
    if any(set(shard) != keys for shard in shards[1:]):
        raise ValueError("rollout shards have different array schemas")
    arrays = {key: np.concatenate([shard[key] for shard in shards], axis=0) for key in keys}
    advantage = arrays["advantage"].astype(np.float32)
    advantage_normalization = {}
    layer_names = {
        0: "gold_train", 1: "ppo_history", 2: "self_play", 3: "exploiter", 4: "anchor",
    }
    if "opponent_layer_id" in arrays and np.any(arrays["opponent_layer_id"] >= 0):
        normalized = advantage.copy()
        for layer_id in sorted(int(value) for value in np.unique(arrays["opponent_layer_id"]) if value >= 0):
            selected = arrays["opponent_layer_id"] == layer_id
            mean = float(advantage[selected].mean())
            std = max(1e-6, float(advantage[selected].std()))
            normalized[selected] = (advantage[selected] - mean) / std
            advantage_normalization[layer_names.get(layer_id, str(layer_id))] = {
                "rows": int(selected.sum()), "mean": mean, "std": std,
            }
        arrays["advantage"] = normalized.astype(np.float32)
        normalization_scope = "per_opponent_layer"
    else:
        mean = float(advantage.mean())
        std = max(1e-6, float(advantage.std()))
        arrays["advantage"] = ((advantage - mean) / std).astype(np.float32)
        advantage_normalization["all"] = {"rows": len(advantage), "mean": mean, "std": std}
        normalization_scope = "global"
    rows = [row for report in reports for row in report.get("rows", [])]
    report = {
        "schema": "kaggriculture-v113-merged-rollouts-v1",
        "inputs": [str(path) for path in args.input],
        "games": len(rows),
        "transitions": len(arrays["advantage"]),
        "score_rate": float(np.mean([row["score"] for row in rows])),
        "mean_candidate_reward": float(np.mean([row["candidate_reward"] for row in rows])),
        "mean_margin": float(np.mean([row["margin"] for row in rows])),
        "done_done": sum(row["statuses"] == ["DONE", "DONE"] for row in rows),
        "accepted_games": sum(row.get("accepted_for_training", True) for row in rows),
        "rejected_games": sum(not row.get("accepted_for_training", True) for row in rows),
        "elapsed_seconds_sum": float(sum(item.get("elapsed_seconds", 0.0) for item in reports)),
        "advantage_normalized": True,
        "advantage_normalization_scope": normalization_scope,
        "advantage_normalization": advantage_normalization,
        "opponent_registry": reports[0].get("opponent_registry"),
        "opponent_schedules": [report.get("opponent_schedule") for report in reports],
        **contract,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    args.output.with_suffix(".json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: report[key] for key in (
        "games", "transitions", "score_rate", "mean_candidate_reward",
        "mean_margin", "done_done", "elapsed_seconds_sum",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
