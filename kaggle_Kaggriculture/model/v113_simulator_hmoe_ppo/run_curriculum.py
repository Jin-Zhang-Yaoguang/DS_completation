"""Resumable PPO curriculum loop; each iteration uses fresh seeds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent


def run(command):
    print(json.dumps({"command": command}, ensure_ascii=False), flush=True)
    subprocess.run(command, cwd=HERE, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--opponent", default="builtin:pass")
    parser.add_argument("--iterations", type=int, default=6)
    parser.add_argument("--seeds-per-iteration", type=int, default=4)
    parser.add_argument("--seed-start", type=int, default=1133000)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--min-mean-reward", type=float, default=10000.0)
    parser.add_argument("--min-reward-improvement", type=float, default=100.0)
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    current = args.checkpoint.resolve()
    history = []
    started = time.time()
    evaluation_seed = args.seed_start + 100000
    baseline_evaluation = args.output_root / "baseline_evaluation.json"
    run([
        sys.executable, str(HERE / "evaluate_bc_closed_loop.py"), "--checkpoint", str(current),
        "--opponent", args.opponent, "--seeds", "2", "--seed-start", str(evaluation_seed),
        "--output", str(baseline_evaluation), "--min-mean-reward", str(args.min_mean_reward),
    ])
    baseline = json.loads(baseline_evaluation.read_text(encoding="utf-8"))
    best_metric = (baseline["score_rate"], baseline["mean_candidate_reward"], baseline["mean_margin"])
    for iteration in range(args.iterations):
        folder = args.output_root / f"iter_{iteration:03d}"
        folder.mkdir(parents=True, exist_ok=True)
        rollout = folder / "rollouts.npz"
        seed = args.seed_start + iteration * args.seeds_per_iteration
        run([
            sys.executable, str(HERE / "collect_rollouts.py"), "--checkpoint", str(current),
            "--opponent", args.opponent, "--seeds", str(args.seeds_per_iteration),
            "--seed-start", str(seed), "--output", str(rollout),
        ])
        run([
            sys.executable, str(HERE / "train_ppo.py"), "--checkpoint", str(current),
            "--rollouts", str(rollout), "--output-dir", str(folder), "--epochs", "4",
            "--batch-size", "256", "--learning-rate", "0.0001", "--seed", str(seed + 1),
        ])
        challenger = (folder / "ppo_checkpoint.msgpack").resolve()
        evaluation = folder / "evaluation.json"
        run([
            sys.executable, str(HERE / "evaluate_bc_closed_loop.py"), "--checkpoint", str(challenger),
            "--opponent", args.opponent, "--seeds", "2", "--seed-start", str(evaluation_seed),
            "--output", str(evaluation), "--min-mean-reward", str(args.min_mean_reward),
        ])
        report = json.loads(evaluation.read_text(encoding="utf-8"))
        challenger_metric = (report["score_rate"], report["mean_candidate_reward"], report["mean_margin"])
        score_improved = challenger_metric[0] > best_metric[0]
        reward_improved = challenger_metric[0] == best_metric[0] and challenger_metric[1] >= best_metric[1] + args.min_reward_improvement
        accepted = score_improved or reward_improved
        if accepted:
            current = challenger
            best_metric = challenger_metric
        row = {
            "iteration": iteration,
            "accepted": accepted,
            "challenger_checkpoint": str(challenger),
            "checkpoint": str(current),
            "rollout": json.loads(rollout.with_suffix(".json").read_text(encoding="utf-8")),
            "evaluation": {key: report[key] for key in ("status", "score_rate", "mean_candidate_reward", "mean_margin", "done_done")},
        }
        history.append(row)
        state = {
            "schema": "kaggriculture-v113-curriculum-loop-v1",
            "status": "COMPLETE" if report["status"] == "PASS_TO_PPO" else "IN_PROGRESS",
            "opponent": args.opponent,
            "initial_checkpoint": str(args.checkpoint),
            "current_checkpoint": str(current),
            "history": history,
            "elapsed_seconds": time.time() - started,
        }
        (args.output_root / "loop_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if accepted and report["status"] == "PASS_TO_PPO":
            break
    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
