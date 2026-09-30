"""JAX/Flax model and export helpers for the v3 macro policy."""

from __future__ import annotations

from pathlib import Path

import flax.linen as nn
from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np

import main


class MacroPolicy(nn.Module):
    @nn.compact
    def __call__(self, features, hidden):
        features = jnp.clip(features, -5.0, 5.0)
        encoded = jnp.tanh(nn.Dense(128, name="enc")(features))
        z = nn.sigmoid(
            nn.Dense(main.HIDDEN_SIZE, name="z_x")(encoded)
            + nn.Dense(main.HIDDEN_SIZE, use_bias=False, name="z_h")(hidden)
        )
        r = nn.sigmoid(
            nn.Dense(main.HIDDEN_SIZE, name="r_x")(encoded)
            + nn.Dense(main.HIDDEN_SIZE, use_bias=False, name="r_h")(hidden)
        )
        candidate = jnp.tanh(
            nn.Dense(main.HIDDEN_SIZE, name="n_x")(encoded)
            + nn.Dense(main.HIDDEN_SIZE, use_bias=False, name="n_h")(r * hidden)
        )
        next_hidden = z * hidden + (1.0 - z) * candidate
        trunk = jnp.tanh(nn.Dense(128, name="mlp")(next_hidden))
        logits = tuple(
            nn.Dense(size, name=f"head_{index}")(trunk)
            for index, size in enumerate(main.HEAD_SIZES)
        )
        value = nn.Dense(1, name="value")(trunk)[..., 0]
        return logits, value, next_hidden


def initial_params(seed=0):
    model = MacroPolicy()
    return model.init(
        jax.random.PRNGKey(seed),
        jnp.zeros((1, main.FEATURE_DIM), dtype=jnp.float32),
        jnp.zeros((1, main.HIDDEN_SIZE), dtype=jnp.float32),
    )


def apply_sequence(model, params, features, initial_hidden=None):
    """Apply recurrent policy to [batch, time, feature] tensors."""
    features = jnp.asarray(features, dtype=jnp.float32)
    batch = features.shape[0]
    hidden = (
        jnp.zeros((batch, main.HIDDEN_SIZE), dtype=jnp.float32)
        if initial_hidden is None
        else jnp.asarray(initial_hidden, dtype=jnp.float32)
    )

    def scan_step(carry, step_features):
        logits, value, next_hidden = model.apply(params, step_features, carry)
        return next_hidden, (*logits, value)

    final_hidden, outputs = jax.lax.scan(scan_step, hidden, jnp.swapaxes(features, 0, 1))
    logits = tuple(jnp.swapaxes(output, 0, 1) for output in outputs[:-1])
    values = jnp.swapaxes(outputs[-1], 0, 1)
    return logits, values, final_hidden


def save_checkpoint(path, params):
    Path(path).write_bytes(serialization.to_bytes(params))


def load_checkpoint(path, template=None):
    template = initial_params() if template is None else template
    return serialization.from_bytes(template, Path(path).read_bytes())


def export_numpy(params, path):
    p = params["params"]
    arrays = {
        "schema": np.asarray(main.SCHEMA_VERSION),
        "feature_dim": np.asarray(main.FEATURE_DIM, dtype=np.int32),
        # The encoder already performs deterministic domain normalization.
        # Keep its affine parameters in the artifact so the deployment schema
        # can evolve without changing the submission interface.
        "feature_offset": np.asarray(main.FEATURE_OFFSET, dtype=np.float32),
        "feature_scale": np.asarray(main.FEATURE_SCALE, dtype=np.float32),
        "enc_w": np.asarray(p["enc"]["kernel"], dtype=np.float32),
        "enc_b": np.asarray(p["enc"]["bias"], dtype=np.float32),
        "z_x_w": np.asarray(p["z_x"]["kernel"], dtype=np.float32),
        "z_x_b": np.asarray(p["z_x"]["bias"], dtype=np.float32),
        "z_h_w": np.asarray(p["z_h"]["kernel"], dtype=np.float32),
        "r_x_w": np.asarray(p["r_x"]["kernel"], dtype=np.float32),
        "r_x_b": np.asarray(p["r_x"]["bias"], dtype=np.float32),
        "r_h_w": np.asarray(p["r_h"]["kernel"], dtype=np.float32),
        "n_x_w": np.asarray(p["n_x"]["kernel"], dtype=np.float32),
        "n_x_b": np.asarray(p["n_x"]["bias"], dtype=np.float32),
        "n_h_w": np.asarray(p["n_h"]["kernel"], dtype=np.float32),
        "mlp_w": np.asarray(p["mlp"]["kernel"], dtype=np.float32),
        "mlp_b": np.asarray(p["mlp"]["bias"], dtype=np.float32),
        "value_w": np.asarray(p["value"]["kernel"], dtype=np.float32),
        "value_b": np.asarray(p["value"]["bias"], dtype=np.float32),
    }
    for index in range(len(main.HEAD_SIZES)):
        arrays[f"head_{index}_w"] = np.asarray(p[f"head_{index}"]["kernel"], dtype=np.float32)
        arrays[f"head_{index}_b"] = np.asarray(p[f"head_{index}"]["bias"], dtype=np.float32)
    np.savez_compressed(path, **arrays)
    return arrays


def parity_error(params, weight_path, seed=1234, batch=8):
    rng = np.random.default_rng(seed)
    features = rng.normal(size=(batch, main.FEATURE_DIM)).astype(np.float32)
    hidden = rng.normal(size=(batch, main.HIDDEN_SIZE)).astype(np.float32)
    model = MacroPolicy()
    jax_logits, jax_values, jax_hidden = model.apply(params, jnp.asarray(features), jnp.asarray(hidden))
    numpy_policy = main.NumpyPolicy(weight_path)
    numpy_rows = [numpy_policy.step(features[index], hidden[index]) for index in range(batch)]
    errors = []
    for head_index in range(len(main.HEAD_SIZES)):
        expected = np.asarray(jax_logits[head_index])
        actual = np.stack([row[0][head_index] for row in numpy_rows])
        errors.append(float(np.max(np.abs(expected - actual))))
    errors.append(float(np.max(np.abs(np.asarray(jax_values) - np.asarray([row[1] for row in numpy_rows])))))
    errors.append(float(np.max(np.abs(np.asarray(jax_hidden) - np.stack([row[2] for row in numpy_rows])))))
    return max(errors)
