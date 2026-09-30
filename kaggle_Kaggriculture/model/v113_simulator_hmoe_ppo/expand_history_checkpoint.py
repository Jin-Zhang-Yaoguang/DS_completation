"""Expand a timed sequence checkpoint from 60 to 92 global input features."""

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
from model_sequence_action import SequenceActionHMoEActorCritic


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=11327)
    args = parser.parse_args()
    source = serialization.msgpack_restore(args.checkpoint.read_bytes())
    model = SequenceActionHMoEActorCritic(timed=True)
    batch = 1
    initialized = model.init(
        jax.random.key(args.seed),
        jnp.zeros((batch, features.GLOBAL_FEATURES + HISTORY_FEATURES)),
        jnp.zeros((batch, 2, features.BOARD_SIZE, features.BOARD_SIZE, features.BOARD_CHANNELS)),
        jnp.zeros((batch, features.MAX_UNITS, features.UNIT_FEATURES)),
        jnp.ones((batch, features.MAX_UNITS)),
        jnp.zeros((batch, features.MAX_UNITS), dtype=jnp.int16),
        jnp.zeros((batch, features.MAX_UNITS), dtype=jnp.int16),
        jnp.zeros((batch, space.MAX_MARKET_SLOTS), dtype=jnp.int16),
        jnp.zeros((batch, space.MAX_MARKET_SLOTS), dtype=jnp.int16),
    )["params"]
    old_flat = traverse_util.flatten_dict(source["params"])
    new_flat = traverse_util.flatten_dict(initialized)
    expanded_key = ("own_global_dense", "kernel")
    copied = 0
    for key, old_value in old_flat.items():
        if key == expanded_key:
            new_value = np.asarray(new_flat[key]).copy()
            old_array = np.asarray(old_value)
            if new_value.shape[0] != old_array.shape[0] + HISTORY_FEATURES:
                raise ValueError(f"unexpected expanded kernel shapes: {old_array.shape} -> {new_value.shape}")
            new_value[:old_array.shape[0]] = old_array
            new_value[old_array.shape[0]:] = 0.0
            new_flat[key] = new_value
        else:
            if key not in new_flat or np.shape(new_flat[key]) != np.shape(old_value):
                raise ValueError(f"incompatible parameter: {key}")
            new_flat[key] = old_value
        copied += 1
    result = {
        **{key: value for key, value in source.items() if key != "params"},
        "params": traverse_util.unflatten_dict(new_flat),
        "architecture": "history32-timed-joint-autoregressive-action-hmoe-v1",
        "history_features": HISTORY_FEATURES,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=args.output.parent, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(result))
        temporary = Path(sink.name)
    temporary.replace(args.output)
    print(json.dumps({
        "source": str(args.checkpoint), "output": str(args.output),
        "copied_parameters": copied, "history_features": HISTORY_FEATURES,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
