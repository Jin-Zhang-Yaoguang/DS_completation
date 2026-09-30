"""Relabel valid on-policy rollouts with a pure terminal own-score return."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gamma", type=float, default=0.999)
    parser.add_argument("--score-scale", type=float, default=3000.0)
    parser.add_argument(
        "--terminal-mode", choices=("own-log", "smooth-margin"), default="own-log"
    )
    parser.add_argument("--margin-scale", type=float, default=100000.0)
    parser.add_argument("--no-normalize-advantage", action="store_true")
    args = parser.parse_args()
    if not 0.0 < args.gamma <= 1.0:
        parser.error("--gamma must be in (0, 1]")
    if args.score_scale <= 0.0:
        parser.error("--score-scale must be positive")
    if args.margin_scale <= 0.0:
        parser.error("--margin-scale must be positive")

    report_path = args.input.with_suffix(".json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    with np.load(args.input) as archive:
        arrays = {key: archive[key] for key in archive.files}
    keys = list(zip(arrays["episode_seed"].tolist(), arrays["seat"].tolist()))
    row_by_key = {(int(row["seed"]), int(row["seat"])): row for row in report["rows"]}
    if set(keys) != set(row_by_key):
        raise ValueError("rollout arrays and sidecar rows have different episode/seat keys")

    reward = np.zeros(len(keys), dtype=np.float32)
    returns = np.zeros(len(keys), dtype=np.float32)
    start = 0
    groups = []
    while start < len(keys):
        key = keys[start]
        end = start + 1
        while end < len(keys) and keys[end] == key:
            end += 1
        if key in {item["key"] for item in groups}:
            raise ValueError(f"non-contiguous trajectory for {key}")
        if args.terminal_mode == "smooth-margin":
            terminal = float(np.tanh(float(row_by_key[key]["margin"]) / args.margin_scale))
        else:
            terminal = float(np.log1p(
                max(0.0, row_by_key[key]["candidate_reward"]) / args.score_scale
            ))
        reward[end - 1] = terminal
        horizon = end - start
        returns[start:end] = terminal * np.power(
            args.gamma, np.arange(horizon - 1, -1, -1, dtype=np.float32)
        )
        groups.append({"key": key, "transitions": horizon, "terminal_return": terminal})
        start = end

    advantage = returns.copy()
    if not args.no_normalize_advantage:
        advantage = (
            (advantage - advantage.mean()) / max(1e-6, float(advantage.std()))
        ).astype(np.float32)
    arrays["reward"] = reward
    arrays["return_target"] = returns
    arrays["value_prediction"] = np.zeros_like(returns)
    arrays["advantage"] = advantage

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    output_report = {
        **report,
        "schema": "kaggriculture-v113-relabelled-terminal-rollouts-v1",
        "source": str(args.input),
        "gamma": args.gamma,
        "lambda_gae": 1.0,
        "potential": "none",
        "terminal_mode": args.terminal_mode,
        "ignore_value_baseline": True,
        "advantage_normalized": not args.no_normalize_advantage,
        "score_scale": args.score_scale,
        "margin_scale": args.margin_scale,
        "trajectory_count": len(groups),
        "return_mean": float(returns.mean()),
        "return_std": float(returns.std()),
    }
    args.output.with_suffix(".json").write_text(
        json.dumps(output_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: output_report[key] for key in (
        "trajectory_count", "transitions", "return_mean", "return_std",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
