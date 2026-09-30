"""Generate compact daily behavior-cloning trajectories from frozen v2."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time

import numpy as np


HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE.parent
_MODULE_CACHE = {}


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _market_variant(module, scale):
    def opponent(obs):
        action = module.agent(obs)
        copied = {
            "farmer": list(action.get("farmer") or ["PASS"]),
            "hands": [list(order or ["PASS"]) for order in list(action.get("hands") or [])],
            "market": [list(order) for order in list(action.get("market") or [])],
        }
        for order in copied["market"]:
            if len(order) >= 3 and order[0] == "SELL":
                order[2] = max(0, int(round(int(order[2] or 0) * scale)))
        return copied

    return opponent


def _forced_route(module, route):
    def opponent(obs):
        module._ACTIONS = module._HIGH_ROUTE_ACTIONS if route == 1 else module._LOW_ROUTE_ACTIONS
        return module._CORE_AGENT(obs)

    return opponent


def _episode(task):
    index, seed, seat, opponent_name = task
    import main
    import base_agent
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg

    process_id = os.getpid()
    if "v0" not in _MODULE_CACHE:
        _MODULE_CACHE["v0"] = _load_module(MODEL_DIR / "v0_api_smoke" / "main.py", f"v0_worker_{process_id}")
        _MODULE_CACHE["v1"] = _load_module(MODEL_DIR / "v1_adaptive_market" / "main.py", f"v1_worker_{process_id}")
    v0 = _MODULE_CACHE["v0"]
    v1 = _MODULE_CACHE["v1"]
    opponent = {
        "v0": v0.agent,
        "v1": v1.agent,
        "v2": base_agent.agent,
        "starter": kg.starter_agent,
        "random": kg.random_agent,
        "forced_low": _forced_route(base_agent, 0),
        "forced_high": _forced_route(base_agent, 1),
        "market_half": _market_variant(base_agent, 0.5),
        "market_double": _market_variant(base_agent, 2.0),
    }[opponent_name]

    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    history = {}
    macro = main.DEFAULT_MACRO.copy()
    sticky_route = 0
    features = []
    labels = []
    route_mask = []
    potentials = []

    for step in range(719):
        # The low-level manual stepping API only advances `step` on player 0's
        # Struct.  env.run injects it for both agents, so mirror that behavior
        # here or every seat-1 replay would execute route step zero forever.
        env.state[0].observation.step = step
        env.state[1].observation.step = step
        teacher_obs = env.state[seat].observation
        day = int(teacher_obs.get("day", step // 24) or 0)
        hour = int(teacher_obs.get("hour", step % 24) or 0)
        if hour == 0:
            # Encode the macro that was active on the previous day.  Computing
            # today's teacher label first would leak the day-7 route decision
            # into the observation used to predict that same decision.
            features.append(main.encode_observation(teacher_obs, history, macro))
            if day == 7:
                sticky_route = main.teacher_route(teacher_obs)
            next_macro = main.DEFAULT_MACRO.copy()
            next_macro[0] = sticky_route
            labels.append(next_macro.copy())
            route_mask.append(day == 7)
            potentials.append(main.potential(teacher_obs))
            history = main.update_history(teacher_obs, next_macro)
            macro = next_macro

        teacher_action = base_agent.agent(teacher_obs)
        opponent_obs = env.state[1 - seat].observation
        opponent_action = opponent(opponent_obs)
        actions = [teacher_action, opponent_action] if seat == 0 else [opponent_action, teacher_action]
        env.step(actions)

    final = env.state
    rewards = [float(state.reward or 0.0) for state in final]
    statuses = [str(state.status) for state in final]
    if statuses != ["DONE", "DONE"] or len(features) != 30:
        raise RuntimeError((index, seed, statuses, len(features)))
    return {
        "index": index,
        "seed": int(seed),
        "seat": int(seat),
        "opponent": opponent_name,
        "features": np.asarray(features, dtype=np.float32),
        "actions": np.asarray(labels, dtype=np.int16),
        "route_mask": np.asarray(route_mask, dtype=np.bool_),
        "potentials": np.asarray(potentials, dtype=np.float32),
        "rewards": np.asarray(rewards, dtype=np.float32),
    }


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _save_shard(output, shard_index, rows):
    rows.sort(key=lambda row: row["index"])
    path = output / f"bc-{shard_index:04d}.npz"
    np.savez_compressed(
        path,
        features=np.stack([row["features"] for row in rows]),
        actions=np.stack([row["actions"] for row in rows]),
        route_mask=np.stack([row["route_mask"] for row in rows]),
        potentials=np.stack([row["potentials"] for row in rows]),
        seeds=np.asarray([row["seed"] for row in rows], dtype=np.int64),
        seats=np.asarray([row["seat"] for row in rows], dtype=np.int8),
        opponents=np.asarray([row["opponent"] for row in rows]),
        rewards=np.stack([row["rewards"] for row in rows]),
    )
    return {"file": path.name, "episodes": len(rows), "sha256": _sha256(path)}


def collect(episodes, workers, output, start_seed, shard_size=1000):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    opponents = (
        "v2", "v2", "v0", "v1", "starter", "random",
        "forced_low", "forced_high", "market_half", "market_double",
    )
    tasks = [
        (index, int((start_seed + index * 7919) % (2**31 - 1)), index % 2, opponents[index % len(opponents)])
        for index in range(episodes)
    ]
    started = time.time()
    pending = []
    shards = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_episode, task) for task in tasks]
        for completed, future in enumerate(as_completed(futures), start=1):
            pending.append(future.result())
            if len(pending) >= shard_size or completed == episodes:
                shards.append(_save_shard(output, len(shards), pending))
                pending = []
            if completed % max(1, min(100, episodes // 10)) == 0 or completed == episodes:
                elapsed = time.time() - started
                print(json.dumps({"completed": completed, "episodes": episodes, "episodes_per_second": completed / max(elapsed, 1e-6)}), flush=True)
    manifest = {
        "schema": "kaggriculture-v3-bc-1",
        "feature_schema": __import__("main").SCHEMA_VERSION,
        "feature_dim": __import__("main").FEATURE_DIM,
        "episodes": episodes,
        "workers": workers,
        "start_seed": start_seed,
        "opponents": list(opponents),
        "split": "sha256(seed) mod 100: train 0-79, validation 80-89, test 90-99",
        "base_agent_sha256": _sha256(HERE / "base_agent.py"),
        "source_sha256": {
            name: _sha256(HERE / name)
            for name in ("collect_bc.py", "main.py", "base_agent.py")
        },
        "elapsed_seconds": time.time() - started,
        "shards": shards,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=10000)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--start-seed", type=int, default=31000000)
    parser.add_argument("--shard-size", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=HERE / "data" / "bc")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(collect(args.episodes, args.workers, args.output, args.start_seed, args.shard_size), ensure_ascii=False, indent=2))
