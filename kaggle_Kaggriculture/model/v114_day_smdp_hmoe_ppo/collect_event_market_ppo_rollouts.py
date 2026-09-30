"""Collect official-simulator V12 event-market SMDP rollouts."""

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


def atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", suffix=".npz", dir=path.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(path)


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def run_game(unit_checkpoint: str, market_checkpoint: str, seed: int, seat: int, output: str) -> dict:
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture
    from event_ledger_controller import EventLedgerController
    from persistent_unit_tasks import PersistentUnitTaskExecutor, UnitTaskBCPolicy
    from policy_trainable_event_market import TrainableEventMarketPolicy

    unit = UnitTaskBCPolicy(Path(unit_checkpoint))
    executor = PersistentUnitTaskExecutor(unit)
    market = TrainableEventMarketPolicy(
        Path(market_checkpoint), rollout_seed=(seed * 2 + seat) & 0xFFFFFFFF
    )
    controller = EventLedgerController(executor.act, market)
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
    final_observation = env.steps[-1][seat].observation
    transitions = market.finalize_episode(final_observation)
    target = Path(output)
    if transitions:
        arrays = {}
        for key, dtype in (
            ("global", np.float16), ("board", np.float16),
            ("event_type", np.int8), ("presence_action", np.int8),
            ("quantity_action", np.int8), ("presence_mask", np.bool_),
            ("quantity_mask", np.bool_), ("old_logp", np.float32),
            ("old_entropy", np.float32), ("value", np.float32),
            ("start_step", np.int16), ("end_step", np.int16),
            ("duration_turns", np.int16), ("reward", np.float32),
            ("terminal", np.bool_),
        ):
            arrays[key] = np.asarray([row[key] for row in transitions], dtype=dtype)
        arrays["seed"] = np.full(len(transitions), seed, np.int64)
        arrays["seat"] = np.full(len(transitions), seat, np.int8)
        arrays["episode_return"] = np.full(len(transitions), rewards[seat], np.float32)
        atomic_npz(target, arrays)
    valid = error is None and statuses == ["DONE", "DONE"] and len(env.steps) == 720
    ledger = controller.audit()["ledger"]
    return {
        "seed": seed, "seat": seat, "valid": valid, "error": error,
        "candidate_reward": rewards[seat], "opponent_reward": rewards[1 - seat],
        "rows": len(transitions), "output": str(target.resolve()) if target.exists() else None,
        "output_sha256": hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None,
        "unit": executor.audit(), "ledger": ledger,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit-checkpoint", type=Path, required=True)
    parser.add_argument("--market-checkpoint", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seed-blocks", type=int, default=4)
    parser.add_argument("--workers", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    assignments = [(args.seed_start + offset, seat) for offset in range(args.seed_blocks) for seat in (0, 1)]
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                run_game, str(args.unit_checkpoint), str(args.market_checkpoint), seed, seat,
                str(args.output_dir / f"rollout_seed{seed}_seat{seat}.npz"),
            ): (seed, seat) for seed, seat in assignments
        }
        for future in as_completed(futures):
            row = future.result(); rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    rows.sort(key=lambda row: (row["seed"], row["seat"]))
    manifest = {
        "schema": "kaggriculture-v114-v12-event-market-on-policy-v1",
        "status": "ON_POLICY_EVENT_MARKET_DATA_NOT_G2_NOT_GOLD",
        "unit_checkpoint_sha256": hashlib.sha256(args.unit_checkpoint.read_bytes()).hexdigest(),
        "market_checkpoint_sha256": hashlib.sha256(args.market_checkpoint.read_bytes()).hexdigest(),
        "seed_start": args.seed_start, "seed_blocks": args.seed_blocks,
        "fresh_evidence": False, "opponent": "builtin:starter",
        "games": len(rows), "valid_games": sum(row["valid"] for row in rows),
        "transitions": sum(row["rows"] for row in rows), "rows": rows,
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.manifest, manifest)
    print(json.dumps({key: manifest[key] for key in ("games", "valid_games", "transitions", "elapsed_seconds")}, indent=2))
    if manifest["valid_games"] != manifest["games"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
