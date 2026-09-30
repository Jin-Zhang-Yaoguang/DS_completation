"""Run the BC policy in the official engine before allowing PPO."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

from kaggle_environments import make

from policy import V113Policy


def load_agent(path: Path, name: str):
    path = path.resolve()
    agent_dir = path.parent
    # Kaggle archives commonly use flat sibling imports (for example
    # ``import base_agent``).  Recreate that archive import contract while
    # loading, and discard stale sibling modules from a previous episode so
    # module-level agent state does not leak between paired games.
    sibling_names = {candidate.stem for candidate in agent_dir.glob("*.py")}
    for module_name, loaded_module in list(sys.modules.items()):
        if module_name.split(".", 1)[0] in sibling_names:
            del sys.modules[module_name]
            continue
        module_file = getattr(loaded_module, "__file__", None)
        if module_file is None:
            continue
        try:
            if Path(module_file).resolve().is_relative_to(agent_dir):
                del sys.modules[module_name]
        except (OSError, RuntimeError, ValueError):
            continue
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.path.insert(0, str(agent_dir))
    try:
        spec.loader.exec_module(module)
    finally:
        try:
            sys.path.remove(str(agent_dir))
        except ValueError:
            pass
    return module.agent


def resolve_opponent(value: str, name: str):
    if value.startswith("builtin:"):
        from kaggle_environments.envs.kaggriculture import kaggriculture
        agents = {"pass": kaggriculture.pass_agent, "random": kaggriculture.random_agent, "starter": kaggriculture.starter_agent}
        return agents[value.split(":", 1)[1]]
    return load_agent(Path(value), name)


def score(margin: float) -> float:
    return 1.0 if margin > 0 else (0.5 if margin == 0 else 0.0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--seeds", type=int, default=2)
    parser.add_argument("--seed-start", type=int, default=1131000)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-mean-reward", type=float, default=10000.0)
    parser.add_argument("--forced-expert", type=int)
    parser.add_argument("--expert-schedule", help="comma-separated 30-day expert ids")
    parser.add_argument("--opponent-blind", action="store_true")
    args = parser.parse_args()
    expert_schedule = None
    if args.expert_schedule:
        expert_schedule = [int(value) for value in args.expert_schedule.split(",")]
        if len(expert_schedule) != 30:
            parser.error("--expert-schedule requires exactly 30 comma-separated ids")
    started = time.time()
    rows = []
    for seed in range(args.seed_start, args.seed_start + args.seeds):
        for seat in (0, 1):
            candidate = V113Policy(
                args.checkpoint, forced_expert=args.forced_expert,
                expert_schedule=expert_schedule,
                opponent_blind=args.opponent_blind,
            )
            opponent = resolve_opponent(args.opponent, f"v113_opponent_{seed}_{seat}")
            agents = [None, None]
            agents[seat] = candidate
            agents[1 - seat] = opponent
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
            error = None
            try:
                env.run(agents)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            rewards = [float(state.reward or 0.0) for state in env.state]
            statuses = [str(state.status) for state in env.state]
            margin = rewards[seat] - rewards[1 - seat]
            rows.append({
                "seed": seed,
                "seat": seat,
                "candidate_reward": rewards[seat],
                "opponent_reward": rewards[1 - seat],
                "margin": margin,
                "score": score(margin),
                "statuses": statuses,
                "steps": len(env.steps),
                "error": error,
                "expert_usage": dict(candidate.expert_usage),
                "operation_counts": dict(candidate.operation_counts),
                "nonpass_unit_orders": candidate.nonpass_unit_orders,
            })
            print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    valid = [row for row in rows if row["error"] is None and row["statuses"] == ["DONE", "DONE"]]
    report = {
        "schema": "kaggriculture-v113-bc-closed-loop-v1",
        "status": "PASS_TO_PPO" if len(valid) == len(rows) and statistics.mean(row["candidate_reward"] for row in valid) >= args.min_mean_reward else "FAIL_REQUIRES_MORE_BC",
        "games": len(rows),
        "done_done": len(valid),
        "score_rate": statistics.mean(row["score"] for row in valid) if valid else 0.0,
        "mean_candidate_reward": statistics.mean(row["candidate_reward"] for row in valid) if valid else 0.0,
        "mean_margin": statistics.mean(row["margin"] for row in valid) if valid else 0.0,
        "min_mean_reward_gate": args.min_mean_reward,
        "elapsed_seconds": time.time() - started,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, delete=False) as sink:
        json.dump(report, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(args.output)
    print(json.dumps({key: report[key] for key in ("status", "games", "done_done", "score_rate", "mean_candidate_reward", "mean_margin", "elapsed_seconds")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
