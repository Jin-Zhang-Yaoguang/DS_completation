"""Collect V12 on-policy task-boundary rollouts in the official simulator."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

import numpy as np


def _atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", suffix=".npz", dir=path.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(path)


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def _stack(transitions: list[dict], seed: int, seat: int) -> dict[str, np.ndarray]:
    if not transitions:
        raise ValueError("rollout produced no task transitions")
    arrays: dict[str, np.ndarray] = {
        "global": np.stack([row["global"] for row in transitions]).astype(np.float16),
        "board": np.stack([row["board"] for row in transitions]).astype(np.float16),
        "unit": np.stack([row["unit"] for row in transitions]).astype(np.float16),
    }
    for name in transitions[0]["candidates"]:
        arrays[f"candidate_{name}"] = np.stack([
            row["candidates"][name] for row in transitions
        ])
    for name, dtype in (
        ("action", np.int16), ("unit_index", np.int16),
        ("start_step", np.int16), ("end_step", np.int16),
        ("duration_turns", np.int16),
        ("old_logp", np.float32), ("old_entropy", np.float32),
        ("value", np.float32), ("reward", np.float32),
        ("episode_terminal_reward", np.float32), ("terminal", np.bool_),
    ):
        arrays[name] = np.asarray([row[name] for row in transitions], dtype=dtype)
    arrays["operation"] = np.asarray([row["operation"] for row in transitions], dtype="U24")
    arrays["status"] = np.asarray([row["status"] for row in transitions], dtype="U24")
    arrays["seed"] = np.full(len(transitions), seed, np.int64)
    arrays["seat"] = np.full(len(transitions), seat, np.int8)
    return arrays


def run_game(checkpoint: str, seed: int, seat: int, output_path: str) -> dict:
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture

    from event_ledger_controller import EventLedgerController
    from persistent_unit_tasks import PersistentUnitTaskExecutor
    from policy_event_ledger_v12 import BootstrapEventMarketPolicy
    from policy_unit_task_ppo import UnitTaskPPOPolicy

    rollout_seed = (int(seed) * 2 + int(seat)) & 0xFFFFFFFF
    planner = UnitTaskPPOPolicy(
        Path(checkpoint), rollout_seed=rollout_seed, deterministic=False, collect=True
    )
    executor = PersistentUnitTaskExecutor(planner)
    controller = EventLedgerController(executor.act, BootstrapEventMarketPolicy())
    def candidate_agent(observation, configuration=None):
        return controller.act(observation)
    agents = [None, None]
    agents[seat], agents[1 - seat] = candidate_agent, kaggriculture.starter_agent
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    error = None
    try:
        env.run(agents)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    rewards = [float(state.reward or 0.0) for state in env.state]
    statuses = [str(state.status) for state in env.state]
    target = Path(output_path)
    valid = error is None and statuses == ["DONE", "DONE"] and len(env.steps) == 720
    transitions = planner.finalize_episode(rewards[seat])
    if transitions:
        arrays = _stack(transitions, seed, seat)
        _atomic_npz(target, arrays)
    return {
        "seed": seed,
        "seat": seat,
        "valid": valid,
        "error": error,
        "statuses": statuses,
        "steps": len(env.steps),
        "candidate_reward": rewards[seat],
        "opponent_reward": rewards[1 - seat],
        "rows": len(transitions),
        "output": str(target.resolve()) if target.exists() else None,
        "output_sha256": hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None,
        "planner": planner.audit(),
        "executor": executor.audit(),
        "ledger": controller.audit(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seed-blocks", type=int, default=2)
    parser.add_argument("--workers", type=int, default=max(1, min(4, os.cpu_count() or 1)))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    assignments = [
        (args.seed_start + offset, seat)
        for offset in range(args.seed_blocks) for seat in (0, 1)
    ]
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {}
        for seed, seat in assignments:
            target = args.output_dir / f"rollout_seed{seed}_seat{seat}.npz"
            futures[pool.submit(
                run_game, str(args.checkpoint), seed, seat, str(target)
            )] = (seed, seat)
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    rows.sort(key=lambda row: (row["seed"], row["seat"]))
    manifest = {
        "schema": "kaggriculture-v114-v12-unit-task-on-policy-v1",
        "status": "ON_POLICY_ENGINEERING_DATA_NOT_G1_NOT_FOUNDATION_NOT_GOLD",
        "checkpoint": str(args.checkpoint.resolve()),
        "checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        "seed_start": args.seed_start,
        "seed_blocks": args.seed_blocks,
        "fresh_evidence": False,
        "opponent": "builtin:starter",
        "games": len(rows),
        "valid_games": sum(row["valid"] for row in rows),
        "transitions": sum(row["rows"] for row in rows),
        "market_actions_owned_by_unit_expert": 0,
        "rows": rows,
        "elapsed_seconds": time.time() - started,
    }
    _atomic_json(args.manifest, manifest)
    print(json.dumps({key: manifest[key] for key in (
        "status", "games", "valid_games", "transitions", "elapsed_seconds"
    )}, ensure_ascii=False, indent=2))
    if manifest["valid_games"] != manifest["games"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
