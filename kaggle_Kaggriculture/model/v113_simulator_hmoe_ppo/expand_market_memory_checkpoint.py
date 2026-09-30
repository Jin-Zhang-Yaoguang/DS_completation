#!/usr/bin/env python3
"""Add a zero-initialized market-only observation-memory branch to a history checkpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from flax import serialization, traverse_util
import jax
import jax.numpy as jnp
import numpy as np

import action_space as space
import features
from action_history import HISTORY_FEATURES
from market_state_history import MARKET_MEMORY_FEATURES
from model_sequence_action import SequenceActionHMoEActorCritic


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=11331)
    args = parser.parse_args()
    source = serialization.msgpack_restore(args.checkpoint.read_bytes())
    model = SequenceActionHMoEActorCritic(
        timed=True, market_memory_features=MARKET_MEMORY_FEATURES,
    )
    initialized = model.init(
        jax.random.key(args.seed),
        jnp.zeros((1, features.GLOBAL_FEATURES + HISTORY_FEATURES + MARKET_MEMORY_FEATURES)),
        jnp.zeros((1, 2, features.BOARD_SIZE, features.BOARD_SIZE, features.BOARD_CHANNELS)),
        jnp.zeros((1, features.MAX_UNITS, features.UNIT_FEATURES)),
        jnp.ones((1, features.MAX_UNITS)),
        jnp.zeros((1, features.MAX_UNITS), dtype=jnp.int16),
        jnp.zeros((1, features.MAX_UNITS), dtype=jnp.int16),
        jnp.zeros((1, space.MAX_MARKET_SLOTS), dtype=jnp.int16),
        jnp.zeros((1, space.MAX_MARKET_SLOTS), dtype=jnp.int16),
    )["params"]
    old_flat = traverse_util.flatten_dict(source["params"])
    new_flat = traverse_util.flatten_dict(initialized)
    for key, old_value in old_flat.items():
        if key not in new_flat or np.shape(new_flat[key]) != np.shape(old_value):
            raise ValueError(f"incompatible parameter: {key}")
        new_flat[key] = old_value
    memory_paths = {
        ("market_memory_dense", "kernel"),
        ("market_memory_dense", "bias"),
    }
    if not memory_paths.issubset(new_flat):
        raise ValueError("market memory parameters were not initialized")
    if any(np.any(np.asarray(new_flat[path]) != 0.0) for path in memory_paths):
        raise ValueError("market memory branch must initialize to exact zero")
    result = {
        **{key: value for key, value in source.items() if key != "params"},
        "params": traverse_util.unflatten_dict(new_flat),
        "architecture": "market-memory36-history32-timed-action-hmoe-v1",
        "history_features": HISTORY_FEATURES,
        "market_memory_features": MARKET_MEMORY_FEATURES,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=args.output.parent, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(result))
        temporary = Path(sink.name)
    temporary.replace(args.output)
    print(json.dumps({
        "source": str(args.checkpoint), "output": str(args.output),
        "copied_parameters": len(old_flat),
        "new_zero_parameters": ["/".join(path) for path in sorted(memory_paths)],
        "market_memory_features": MARKET_MEMORY_FEATURES,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
