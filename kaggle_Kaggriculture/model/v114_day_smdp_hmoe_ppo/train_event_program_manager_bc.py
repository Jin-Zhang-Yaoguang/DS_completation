"""BC warm-start for the independent V114 V9 event-program Manager.

The network is always initialized from fresh random parameters.  Training data
may contain only the four V9-1-qualified fixed programs; no historical policy
checkpoint, Gold-Dev, or Gold-Blind artifact is accepted or loaded.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Mapping, Sequence

from flax import serialization
from flax.core import unfreeze
from flax.training.train_state import TrainState
import jax
import jax.numpy as jnp
import numpy as np
import optax

try:
    from .collect_event_program_warmstart import (
        DATASET_SCHEMA,
        FORBIDDEN_LINES,
        QUALIFIED_LINES,
    )
    from .event_ppo_math import HEAD_NAMES, HEAD_SIZES, validate_action_masks
    from .event_program_features import FEATURE_SCHEMA, MANAGER_FEATURE_DIM
    from .model_event_program_ppo import (
        EventProgramPPOManager,
        make_checkpoint_payload,
        validate_checkpoint_metadata,
    )
except ImportError:  # Direct-file CLI execution.
    from collect_event_program_warmstart import (  # type: ignore
        DATASET_SCHEMA,
        FORBIDDEN_LINES,
        QUALIFIED_LINES,
    )
    from event_ppo_math import HEAD_NAMES, HEAD_SIZES, validate_action_masks  # type: ignore
    from event_program_features import FEATURE_SCHEMA, MANAGER_FEATURE_DIM  # type: ignore
    from model_event_program_ppo import (  # type: ignore
        EventProgramPPOManager,
        make_checkpoint_payload,
        validate_checkpoint_metadata,
    )


HERE = Path(__file__).resolve().parent
TRAINING_SCHEMA = "kaggriculture-v114-event-program-manager-bc-training-v1"
SOURCE_FILES = (
    "event_program.py",
    "event_program_features.py",
    "event_ppo_math.py",
    "model_event_program_ppo.py",
    "collect_event_program_warmstart.py",
    "train_event_program_manager_bc.py",
    "policy_random_event_program.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_hashes(root: Path = HERE) -> tuple[dict[str, str], str]:
    per_file: dict[str, str] = {}
    combined = hashlib.sha256()
    for name in SOURCE_FILES:
        digest = sha256_file(root / name)
        per_file[name] = digest
        combined.update(name.encode("utf-8"))
        combined.update(b"\0")
        combined.update(bytes.fromhex(digest))
    return per_file, combined.hexdigest()


def load_dataset(path: Path) -> dict[str, np.ndarray]:
    with np.load(path.expanduser().resolve(), allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def _scalar_text(value: np.ndarray) -> str:
    array = np.asarray(value)
    if array.shape != ():
        raise ValueError("dataset scalar metadata must be zero-dimensional")
    return str(array.item())


def _line_counts(data: Mapping[str, np.ndarray], indices: np.ndarray) -> dict[str, int]:
    counter = Counter(str(value) for value in np.asarray(data["line"])[indices])
    return {line: int(counter.get(line, 0)) for line in QUALIFIED_LINES}


def _require_balanced_lines(
    data: Mapping[str, np.ndarray], indices: np.ndarray, *, label: str
) -> dict[str, int]:
    counts = _line_counts(data, indices)
    if any(count <= 0 for count in counts.values()):
        raise ValueError(f"{label} split must contain all four qualified lines: {counts}")
    if len(set(counts.values())) != 1:
        raise ValueError(f"{label} split is not production-line balanced: {counts}")
    return counts


def validate_dataset(data: Mapping[str, np.ndarray]) -> dict[str, Any]:
    required = {
        "schema", "feature_schema_json", "features", "seed", "seat", "day",
        "step", "line", "candidate_reward", "catastrophe", "error",
        "target_legal", "game_seed", "game_seat", "game_line", "game_error",
    }
    required.update(f"mask_{name}" for name in HEAD_NAMES)
    required.update(f"action_{name}" for name in HEAD_NAMES)
    missing = required - set(data)
    if missing:
        raise ValueError(f"dataset missing keys: {sorted(missing)}")
    if _scalar_text(data["schema"]) != DATASET_SCHEMA:
        raise ValueError("unsupported event-program BC dataset schema")
    if json.loads(_scalar_text(data["feature_schema_json"])) != FEATURE_SCHEMA:
        raise ValueError("dataset feature schema differs from the 427-feature contract")

    features = np.asarray(data["features"])
    if features.ndim != 2 or features.shape[1] != MANAGER_FEATURE_DIM:
        raise ValueError(f"features must have shape [N, {MANAGER_FEATURE_DIM}]")
    if not np.all(np.isfinite(features)):
        raise ValueError("features contain non-finite values")
    rows = features.shape[0]
    for name in ("seed", "seat", "day", "step", "line", "candidate_reward", "catastrophe", "error", "target_legal"):
        if np.asarray(data[name]).shape != (rows,):
            raise ValueError(f"{name} must align with decision rows")

    lines = {str(value) for value in np.asarray(data["line"])}
    game_lines = {str(value) for value in np.asarray(data["game_line"])}
    if lines & FORBIDDEN_LINES or game_lines & FORBIDDEN_LINES:
        raise ValueError("CARROT demonstrations are forbidden")
    if lines != set(QUALIFIED_LINES) or game_lines != set(QUALIFIED_LINES):
        raise ValueError("dataset must contain exactly the four qualified lines")
    if np.any(np.asarray(data["error"]).astype(str) != ""):
        raise ValueError("decision table contains failed-game rows")
    if np.any(np.asarray(data["game_error"]).astype(str) != ""):
        raise ValueError("game table contains errors; training fails closed")
    if not np.all(np.asarray(data["target_legal"], dtype=np.bool_)):
        raise ValueError("one or more teacher labels are illegal under their masks")

    masks = {name: np.asarray(data[f"mask_{name}"]) for name in HEAD_NAMES}
    validate_action_masks(masks, batch_size=rows)
    for name in HEAD_NAMES:
        actions = np.asarray(data[f"action_{name}"])
        if actions.shape != (rows,) or not np.issubdtype(actions.dtype, np.integer):
            raise ValueError(f"action_{name} must be an integer vector")
        if np.any(actions < 0) or np.any(actions >= HEAD_SIZES[name]):
            raise ValueError(f"action_{name} is outside its categorical head")
        if not np.all(masks[name][np.arange(rows), actions.astype(np.int64)]):
            raise ValueError(f"action_{name} contains masked teacher targets")

    all_indices = np.arange(rows, dtype=np.int64)
    line_counts = _require_balanced_lines(data, all_indices, label="full")
    game_keys = list(zip(
        np.asarray(data["game_seed"]).astype(int).tolist(),
        np.asarray(data["game_line"]).astype(str).tolist(),
        np.asarray(data["game_seat"]).astype(int).tolist(),
        strict=True,
    ))
    if len(game_keys) != len(set(game_keys)):
        raise ValueError("game table repeats a seed/line/seat row")
    expected_games = {
        (int(seed), line, seat)
        for seed in np.unique(np.asarray(data["game_seed"]).astype(np.int64))
        for line in QUALIFIED_LINES
        for seat in (0, 1)
    }
    if set(game_keys) != expected_games:
        raise ValueError("game table must contain four lines and both seats per seed")
    return {
        "decision_rows": rows,
        "game_rows": len(game_keys),
        "seed_blocks": int(len(np.unique(np.asarray(data["seed"]).astype(np.int64)))),
        "line_counts": line_counts,
    }


def seed_block_split(
    data: Mapping[str, np.ndarray], *, seed: int, validation_fraction: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not 0.0 < float(validation_fraction) < 1.0:
        raise ValueError("validation_fraction must be between zero and one")
    unique_seeds = np.unique(np.asarray(data["seed"]).astype(np.int64))
    if len(unique_seeds) < 2:
        raise ValueError("BC requires at least two independent seed blocks")
    shuffled = unique_seeds.copy()
    np.random.default_rng(int(seed)).shuffle(shuffled)
    validation_count = min(
        len(shuffled) - 1,
        max(1, int(round(len(shuffled) * float(validation_fraction)))),
    )
    validation_seeds = np.sort(shuffled[:validation_count])
    train_seeds = np.sort(shuffled[validation_count:])
    if set(train_seeds.tolist()) & set(validation_seeds.tolist()):
        raise AssertionError("seed-block split leaked between train and validation")
    sample_seeds = np.asarray(data["seed"]).astype(np.int64)
    train_indices = np.flatnonzero(np.isin(sample_seeds, train_seeds))
    validation_indices = np.flatnonzero(np.isin(sample_seeds, validation_seeds))
    _require_balanced_lines(data, train_indices, label="train")
    _require_balanced_lines(data, validation_indices, label="validation")
    return train_indices, validation_indices, train_seeds, validation_seeds


def masked_cross_entropy(
    logits: jnp.ndarray,
    labels: jnp.ndarray,
    masks: jnp.ndarray,
) -> jnp.ndarray:
    masked_logits = jnp.where(masks, logits, jnp.asarray(-1.0e9, logits.dtype))
    return jnp.mean(
        optax.softmax_cross_entropy_with_integer_labels(
            masked_logits, labels.astype(jnp.int32)
        )
    )


def make_batch(
    data: Mapping[str, np.ndarray],
    indices: Sequence[int] | np.ndarray,
    *,
    reward_center: float,
    reward_scale: float,
) -> dict[str, Any]:
    selected = np.asarray(indices, dtype=np.int64)
    return {
        "features": jnp.asarray(np.asarray(data["features"])[selected], dtype=jnp.float32),
        "masks": {
            name: jnp.asarray(np.asarray(data[f"mask_{name}"])[selected], dtype=jnp.bool_)
            for name in HEAD_NAMES
        },
        "actions": {
            name: jnp.asarray(np.asarray(data[f"action_{name}"])[selected], dtype=jnp.int32)
            for name in HEAD_NAMES
        },
        "value_target": jnp.asarray(
            (np.asarray(data["candidate_reward"])[selected] - reward_center) / reward_scale,
            dtype=jnp.float32,
        ),
        "constraint_target": jnp.asarray(
            np.asarray(data["catastrophe"])[selected], dtype=jnp.float32
        ),
    }


def manager_bc_loss(
    params: Any,
    apply_fn: Any,
    batch: Mapping[str, Any],
    *,
    value_coefficient: float,
    constraint_coefficient: float,
) -> tuple[jnp.ndarray, dict[str, jnp.ndarray]]:
    outputs = apply_fn({"params": params}, batch["features"])
    head_losses = {
        name: masked_cross_entropy(
            outputs["actor_logits"][name], batch["actions"][name], batch["masks"][name]
        )
        for name in HEAD_NAMES
    }
    actor_loss = sum(head_losses.values(), jnp.asarray(0.0, jnp.float32))
    value_loss = jnp.mean((outputs["value"] - batch["value_target"]) ** 2)
    constraint_loss = jnp.mean(
        optax.sigmoid_binary_cross_entropy(
            outputs["constraint_value"], batch["constraint_target"]
        )
    )
    total = (
        actor_loss
        + float(value_coefficient) * value_loss
        + float(constraint_coefficient) * constraint_loss
    )
    metrics = {
        "loss": total,
        "actor_loss": actor_loss,
        "value_loss": value_loss,
        "constraint_loss": constraint_loss,
    }
    metrics.update({f"{name}_loss": loss for name, loss in head_losses.items()})
    return total, metrics


def create_train_state(*, seed: int, learning_rate: float) -> TrainState:
    model = EventProgramPPOManager()
    params = model.init(
        jax.random.PRNGKey(int(seed)),
        jnp.zeros((1, MANAGER_FEATURE_DIM), dtype=jnp.float32),
    )["params"]
    optimizer = optax.chain(
        optax.clip_by_global_norm(0.5),
        optax.adamw(float(learning_rate), weight_decay=1.0e-5),
    )
    return TrainState.create(apply_fn=model.apply, params=params, tx=optimizer)


def train_one_step(
    state: TrainState,
    batch: Mapping[str, Any],
    *,
    value_coefficient: float = 0.1,
    constraint_coefficient: float = 0.1,
) -> tuple[TrainState, dict[str, jnp.ndarray]]:
    def loss_fn(params: Any) -> tuple[jnp.ndarray, dict[str, jnp.ndarray]]:
        return manager_bc_loss(
            params,
            state.apply_fn,
            batch,
            value_coefficient=value_coefficient,
            constraint_coefficient=constraint_coefficient,
        )

    (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(state.params)
    return state.apply_gradients(grads=gradients), metrics


def evaluate(
    state: TrainState,
    data: Mapping[str, np.ndarray],
    indices: np.ndarray,
    *,
    reward_center: float,
    reward_scale: float,
    value_coefficient: float,
    constraint_coefficient: float,
) -> dict[str, Any]:
    batch = make_batch(
        data, indices, reward_center=reward_center, reward_scale=reward_scale
    )
    _, losses = manager_bc_loss(
        state.params,
        state.apply_fn,
        batch,
        value_coefficient=value_coefficient,
        constraint_coefficient=constraint_coefficient,
    )
    outputs = state.apply_fn({"params": state.params}, batch["features"])
    correct: dict[str, np.ndarray] = {}
    for name in HEAD_NAMES:
        logits = jnp.where(
            batch["masks"][name],
            outputs["actor_logits"][name],
            jnp.asarray(-1.0e9, outputs["actor_logits"][name].dtype),
        )
        predicted = np.asarray(jax.device_get(jnp.argmax(logits, axis=-1)))
        truth = np.asarray(jax.device_get(batch["actions"][name]))
        correct[name] = predicted == truth
    joint = np.logical_and.reduce([correct[name] for name in HEAD_NAMES])
    lines = np.asarray(data["line"])[indices].astype(str)
    result = {key: float(jax.device_get(value)) for key, value in losses.items()}
    result["head_accuracy"] = {
        name: float(np.mean(correct[name])) for name in HEAD_NAMES
    }
    result["joint_accuracy"] = float(np.mean(joint))
    result["line_accuracy"] = {
        line: float(np.mean(joint[lines == line])) for line in QUALIFIED_LINES
    }
    result["rows"] = int(len(indices))
    return result


def atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2, sort_keys=True)
        sink.write("\n")
        temporary = Path(sink.name)
    os.replace(temporary, path)


def atomic_checkpoint(path: Path, payload: Mapping[str, Any]) -> str:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = serialization.msgpack_serialize(dict(payload))
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as sink:
        sink.write(encoded)
        temporary = Path(sink.name)
    os.replace(temporary, path)
    return hashlib.sha256(encoded).hexdigest()


def train_bc(args: argparse.Namespace) -> dict[str, Any]:
    if int(args.epochs) <= 0 or int(args.batch_size) <= 0 or int(args.patience) <= 0:
        raise ValueError("epochs, batch_size and patience must be positive")
    if float(args.learning_rate) <= 0 or float(args.reward_scale) <= 0:
        raise ValueError("learning_rate and reward_scale must be positive")
    data = load_dataset(Path(args.dataset))
    dataset_contract = validate_dataset(data)
    train_indices, validation_indices, train_seeds, validation_seeds = seed_block_split(
        data,
        seed=int(args.seed),
        validation_fraction=float(args.validation_fraction),
    )
    dataset_sha = sha256_file(Path(args.dataset).expanduser().resolve())
    source_files, source_sha = source_hashes()
    state = create_train_state(seed=int(args.seed), learning_rate=float(args.learning_rate))
    rng = np.random.default_rng(int(args.seed))
    best_loss = float("inf")
    best_params: Any = None
    best_epoch = 0
    stale_epochs = 0
    history: list[dict[str, Any]] = []
    started = time.time()

    for epoch in range(1, int(args.epochs) + 1):
        order = train_indices.copy()
        rng.shuffle(order)
        training_metrics: list[dict[str, float]] = []
        for start in range(0, len(order), int(args.batch_size)):
            selected = order[start:start + int(args.batch_size)]
            batch = make_batch(
                data,
                selected,
                reward_center=float(args.reward_center),
                reward_scale=float(args.reward_scale),
            )
            state, metrics = train_one_step(
                state,
                batch,
                value_coefficient=float(args.value_coefficient),
                constraint_coefficient=float(args.constraint_coefficient),
            )
            training_metrics.append({
                key: float(jax.device_get(value)) for key, value in metrics.items()
            })
        validation = evaluate(
            state,
            data,
            validation_indices,
            reward_center=float(args.reward_center),
            reward_scale=float(args.reward_scale),
            value_coefficient=float(args.value_coefficient),
            constraint_coefficient=float(args.constraint_coefficient),
        )
        epoch_row = {
            "epoch": epoch,
            "train_loss": float(np.mean([row["loss"] for row in training_metrics])),
            "validation": validation,
        }
        history.append(epoch_row)
        if validation["loss"] < best_loss - float(args.min_delta):
            best_loss = float(validation["loss"])
            best_params = jax.tree_util.tree_map(
                lambda value: np.asarray(jax.device_get(value)), state.params
            )
            best_epoch = epoch
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= int(args.patience):
                break
    if best_params is None:
        raise RuntimeError("training produced no finite validation checkpoint")

    best_state = state.replace(params=best_params)
    final_validation = evaluate(
        best_state,
        data,
        validation_indices,
        reward_center=float(args.reward_center),
        reward_scale=float(args.reward_scale),
        value_coefficient=float(args.value_coefficient),
        constraint_coefficient=float(args.constraint_coefficient),
    )
    payload = make_checkpoint_payload(unfreeze(best_params))
    payload.update({
        "input_dim": MANAGER_FEATURE_DIM,
        "feature_schema": FEATURE_SCHEMA,
        "initialization_seed": int(args.seed),
        "policy_seed": int(args.policy_seed),
        "training_method": "independent_manager_multi_program_bc_warmstart",
        "teacher_programs": list(QUALIFIED_LINES),
        "forbidden_teacher_programs": sorted(FORBIDDEN_LINES),
        "dataset_schema": DATASET_SCHEMA,
        "dataset_sha256": dataset_sha,
        "source_files_sha256": source_files,
        "source_sha256": source_sha,
        "training_seed": int(args.seed),
        "hyperparameters": {
            "epochs": int(args.epochs),
            "batch_size": int(args.batch_size),
            "learning_rate": float(args.learning_rate),
            "validation_fraction": float(args.validation_fraction),
            "patience": int(args.patience),
            "min_delta": float(args.min_delta),
            "value_coefficient": float(args.value_coefficient),
            "constraint_coefficient": float(args.constraint_coefficient),
            "reward_center": float(args.reward_center),
            "reward_scale": float(args.reward_scale),
        },
    })
    validate_checkpoint_metadata(payload)
    checkpoint_sha = atomic_checkpoint(Path(args.output), payload)
    report = {
        "schema": TRAINING_SCHEMA,
        "status": "COMPLETE",
        "lineage": {
            "strategy_parent": None,
            "loads_historical_policy_parameters": False,
            "uses_historical_agent_fallback": False,
        },
        "dataset": {
            "path": str(Path(args.dataset).expanduser().resolve()),
            "sha256": dataset_sha,
            **dataset_contract,
        },
        "split": {
            "unit": "environment_seed_block",
            "train_seeds": train_seeds.tolist(),
            "validation_seeds": validation_seeds.tolist(),
            "overlap": [],
            "train_rows": int(len(train_indices)),
            "validation_rows": int(len(validation_indices)),
            "train_line_counts": _line_counts(data, train_indices),
            "validation_line_counts": _line_counts(data, validation_indices),
        },
        "checkpoint": {
            "path": str(Path(args.output).expanduser().resolve()),
            "sha256": checkpoint_sha,
            "best_epoch": best_epoch,
        },
        "source_files_sha256": source_files,
        "source_sha256": source_sha,
        "training_seed": int(args.seed),
        "policy_seed": int(args.policy_seed),
        "best_validation": final_validation,
        "history": history,
        "early_stopped": len(history) < int(args.epochs),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(Path(args.report), report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=3.0e-4)
    parser.add_argument("--validation-fraction", type=float, default=0.25)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--min-delta", type=float, default=1.0e-4)
    parser.add_argument("--value-coefficient", type=float, default=0.1)
    parser.add_argument("--constraint-coefficient", type=float, default=0.1)
    parser.add_argument("--reward-center", type=float, default=0.0)
    parser.add_argument("--reward-scale", type=float, default=30000.0)
    parser.add_argument("--seed", type=int, default=114920)
    parser.add_argument("--policy-seed", type=int, default=114921)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = train_bc(args)
    print(json.dumps({
        "status": report["status"],
        "checkpoint": report["checkpoint"],
        "best_validation": report["best_validation"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


__all__ = [
    "TRAINING_SCHEMA",
    "create_train_state",
    "load_dataset",
    "make_batch",
    "manager_bc_loss",
    "masked_cross_entropy",
    "seed_block_split",
    "train_bc",
    "train_one_step",
    "validate_dataset",
]
