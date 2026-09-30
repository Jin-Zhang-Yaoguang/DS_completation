"""Read-only teacher-forced diagnostics for a V114 per-slot checkpoint.

This audit measures imitation under teacher forcing.  It deliberately does
not run an environment, access any opponent split, or decide closed-loop
qualification.  High aggregate accuracy can be caused by frequent PASS/STOP
labels and must never be used as a substitute for fresh-seed evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Callable, Mapping

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

import action_space as space  # noqa: E402
from build_per_slot_role_dataset import (  # noqa: E402
    MARKET_ROLE_NAMES,
    OPTION_IDS,
    UNIT_ROLE_NAMES,
)
from model_per_slot_hmoe import PerSlotOptionRoleHMoE  # noqa: E402


MODEL_KEYS = ("global", "board", "units", "unit_mask")
REQUIRED_KEYS = MODEL_KEYS + (
    "teacher_family",
    "option_id",
    "unit_tokens",
    "unit_quantities",
    "unit_roles",
    "market_tokens",
    "market_quantities",
    "market_roles",
    "market_mask",
)

UNIT_CRITICAL_ACTIONS = tuple(
    name for name in space.UNIT_TOKENS
    if name in {
        "DROP", "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP",
        "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE",
    }
    or name.startswith(("PLANT:", "PICKUP:", "PLACE:"))
)
MARKET_CRITICAL_ACTIONS = tuple(
    name for name in space.MARKET_TOKENS if name != "STOP"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return float(numerator / denominator) if denominator else None


def classification_metrics(
    truth: np.ndarray,
    prediction: np.ndarray,
    class_names: tuple[str, ...] | list[str],
    critical_names: tuple[str, ...] = (),
) -> dict:
    """Return unweighted top-1, observed-class macro recall and class recalls."""

    truth = np.asarray(truth, dtype=np.int64).reshape(-1)
    prediction = np.asarray(prediction, dtype=np.int64).reshape(-1)
    if truth.shape != prediction.shape:
        raise ValueError(f"truth/prediction shape mismatch: {truth.shape} != {prediction.shape}")
    if truth.size and (truth.min() < 0 or truth.max() >= len(class_names)):
        raise ValueError("truth contains an out-of-contract class index")
    if prediction.size and (prediction.min() < 0 or prediction.max() >= len(class_names)):
        raise ValueError("prediction contains an out-of-contract class index")

    per_class = {}
    observed_recalls = []
    for index, name in enumerate(class_names):
        selected = truth == index
        support = int(np.sum(selected))
        correct = int(np.sum(selected & (prediction == index)))
        recall = _safe_ratio(correct, support)
        if recall is not None:
            observed_recalls.append(recall)
        per_class[name] = {"support": support, "correct": correct, "recall": recall}

    critical = {name: per_class[name] for name in critical_names if name in per_class}
    supported_critical = [row["recall"] for row in critical.values() if row["recall"] is not None]
    return {
        "support": int(truth.size),
        "top1_accuracy": _safe_ratio(int(np.sum(truth == prediction)), int(truth.size)),
        "macro_recall": float(np.mean(observed_recalls)) if observed_recalls else None,
        "per_class_recall": per_class,
        "critical_action_recall": {
            "macro_recall": float(np.mean(supported_critical)) if supported_critical else None,
            "per_action": critical,
        },
    }


def _binary_idle_metrics(
    truth: np.ndarray,
    prediction: np.ndarray,
    idle_name: str,
) -> dict:
    return classification_metrics(
        np.asarray(truth) != 0,
        np.asarray(prediction) != 0,
        (idle_name, "NONTRIVIAL"),
        ("NONTRIVIAL",),
    )


def _side_metrics(
    truth: np.ndarray,
    prediction: np.ndarray,
    role_truth: np.ndarray,
    role_prediction: np.ndarray,
    mask: np.ndarray,
    action_names: tuple[str, ...],
    role_names: tuple[str, ...],
    critical_actions: tuple[str, ...],
    idle_name: str,
) -> dict:
    active = np.asarray(mask, dtype=bool)
    flat_truth = np.asarray(truth)[active]
    flat_prediction = np.asarray(prediction)[active]
    flat_roles = np.asarray(role_truth)[active]
    flat_role_prediction = np.asarray(role_prediction)[active]

    by_role = {}
    for role_id, role_name in enumerate(role_names):
        selected = flat_roles == role_id
        by_role[role_name] = classification_metrics(
            flat_truth[selected], flat_prediction[selected], action_names, critical_actions
        )

    by_action_type = {}
    for label, selected in (
        (idle_name, flat_truth == 0),
        ("NONTRIVIAL", flat_truth != 0),
    ):
        by_action_type[label] = classification_metrics(
            flat_truth[selected], flat_prediction[selected], action_names, critical_actions
        )

    return {
        "action": classification_metrics(
            flat_truth, flat_prediction, action_names, critical_actions
        ),
        "role_router": classification_metrics(
            flat_roles, flat_role_prediction, role_names
        ),
        "idle_vs_nontrivial": _binary_idle_metrics(
            flat_truth, flat_prediction, idle_name
        ),
        "by_teacher_role": by_role,
        "by_teacher_action_type": by_action_type,
    }


def _slice_predictions(predictions: Mapping[str, np.ndarray], selected: np.ndarray) -> dict:
    return {key: np.asarray(value)[selected] for key, value in predictions.items()}


def _segment_metrics(data: Mapping[str, np.ndarray], predictions: Mapping[str, np.ndarray]) -> dict:
    return {
        "rows": int(len(data["option_id"])),
        "unit": _side_metrics(
            data["unit_tokens"], predictions["unit_tokens"],
            data["unit_roles"], predictions["unit_roles"], data["unit_mask"],
            tuple(space.UNIT_TOKENS), tuple(UNIT_ROLE_NAMES),
            UNIT_CRITICAL_ACTIONS, "PASS",
        ),
        "market": _side_metrics(
            data["market_tokens"], predictions["market_tokens"],
            data["market_roles"], predictions["market_roles"], data["market_mask"],
            tuple(space.MARKET_TOKENS), tuple(MARKET_ROLE_NAMES),
            MARKET_CRITICAL_ACTIONS, "STOP",
        ),
    }


def build_report(
    data: Mapping[str, np.ndarray],
    predictions: Mapping[str, np.ndarray],
    dataset_path: Path,
    checkpoint_path: Path,
    checkpoint_payload: Mapping,
) -> dict:
    rows = len(data["option_id"])
    for key in ("unit_tokens", "unit_roles", "market_tokens", "market_roles"):
        if key not in predictions or len(predictions[key]) != rows:
            raise ValueError(f"prediction {key!r} is missing or has the wrong row count")

    families = np.asarray(data["teacher_family"]).astype(str)
    options = np.asarray(data["option_id"], dtype=np.int64)
    expected_options = np.asarray([OPTION_IDS.get(name, -1) for name in families])
    option_family_mismatches = int(np.sum(expected_options != options))
    by_option_family = {}
    for option_id in sorted(np.unique(options).tolist()):
        option_rows = options == option_id
        option_families = sorted(np.unique(families[option_rows]).tolist())
        for family in option_families:
            selected = option_rows & (families == family)
            segment_data = {key: np.asarray(value)[selected] for key, value in data.items()}
            name = f"option_{option_id}:{family}"
            by_option_family[name] = _segment_metrics(
                segment_data, _slice_predictions(predictions, selected)
            )

    dataset_digest = sha256(dataset_path)
    checkpoint_dataset_digest = checkpoint_payload.get("dataset_sha256")
    return {
        "schema": "kaggriculture-v114-per-slot-checkpoint-audit-v1",
        "epistemic_status": "TEACHER_FORCED_DIAGNOSTIC_ONLY",
        "closed_loop_qualification": False,
        "overall_accuracy_is_closed_loop_gate": False,
        "qualification_warning": (
            "总体准确率会被高频 PASS/STOP 放大；teacher-forced 指标不能证明闭环稳定性，"
            "不能替代 fresh-seed 双座位、多对手、灾难率和金币分布门控。"
        ),
        "data_access": {
            "mode": "READ_ONLY_LOCAL_DATASET_AND_CHECKPOINT",
            "opponent_splits_accessed": [],
            "gold_dev_accessed": False,
            "gold_blind_accessed": False,
        },
        "dataset": str(dataset_path.resolve()),
        "dataset_sha256": dataset_digest,
        "checkpoint": str(checkpoint_path.resolve()),
        "checkpoint_sha256": sha256(checkpoint_path),
        "checkpoint_model_id": checkpoint_payload.get("model_id"),
        "checkpoint_dataset_sha256": checkpoint_dataset_digest,
        "checkpoint_dataset_sha256_matches": (
            checkpoint_dataset_digest == dataset_digest
            if checkpoint_dataset_digest is not None else None
        ),
        "rows": int(rows),
        "option_family_contract": OPTION_IDS,
        "option_family_mismatches": option_family_mismatches,
        "teacher_forcing_contract": {
            "unit": "true prior unit tokens/quantities and true per-unit roles",
            "market": "true unit sequence, prior market tokens/quantities and true per-order roles",
            "role_router": "argmax role prediction is scored separately from conditioned action heads",
        },
        "critical_action_contract": {
            "unit": list(UNIT_CRITICAL_ACTIONS),
            "market": list(MARKET_CRITICAL_ACTIONS),
        },
        "overall": _segment_metrics(data, predictions),
        "by_option_family": by_option_family,
    }


def teacher_forced_predictions(
    data: Mapping[str, np.ndarray],
    checkpoint_payload: Mapping,
    batch_size: int,
) -> dict[str, np.ndarray]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if "params" not in checkpoint_payload:
        raise ValueError("checkpoint is missing params")
    model_id = str(checkpoint_payload.get("model_id", ""))
    if not model_id.startswith("v114_"):
        raise ValueError("checkpoint model_id must identify a V114 model")
    if checkpoint_payload.get("inherits_v113_checkpoint") is not False:
        raise ValueError("checkpoint must explicitly declare inherits_v113_checkpoint=false")

    model = PerSlotOptionRoleHMoE(timed=True)

    @jax.jit
    def apply_batch(params, *inputs):
        return model.apply({"params": params}, *inputs)

    collected = {key: [] for key in (
        "unit_tokens", "unit_roles", "market_tokens", "market_roles"
    )}
    rows = len(data["option_id"])
    for start in range(0, rows, batch_size):
        stop = min(rows, start + batch_size)
        model_batch_keys = MODEL_KEYS + (
            "option_id", "unit_tokens", "unit_quantities", "unit_roles",
            "market_tokens", "market_quantities", "market_roles",
        )
        batch = {
            key: jnp.asarray(np.asarray(data[key])[start:stop])
            for key in model_batch_keys
        }
        output = apply_batch(
            checkpoint_payload["params"], *(batch[key] for key in MODEL_KEYS),
            batch["unit_tokens"], batch["unit_quantities"],
            batch["market_tokens"], batch["market_quantities"],
            batch["unit_roles"], batch["market_roles"],
        )
        option = batch["option_id"].astype(jnp.int32)
        row = jnp.arange(stop - start)
        collected["unit_tokens"].append(np.asarray(
            jnp.argmax(output["unit_logits"][row, option], axis=-1)
        ))
        collected["unit_roles"].append(np.asarray(
            jnp.argmax(output["unit_role_logits"][row, option], axis=-1)
        ))
        collected["market_tokens"].append(np.asarray(
            jnp.argmax(output["market_logits"][row, option], axis=-1)
        ))
        collected["market_roles"].append(np.asarray(
            jnp.argmax(output["market_role_logits"][row, option], axis=-1)
        ))
    return {
        key: np.concatenate(values, axis=0) if values else np.empty((0,), dtype=np.int64)
        for key, values in collected.items()
    }


def audit_checkpoint(
    dataset_path: Path,
    checkpoint_path: Path,
    batch_size: int = 128,
    predictor: Callable[[Mapping[str, np.ndarray], Mapping, int], dict] | None = None,
) -> dict:
    """Load local artifacts read-only and return a JSON-serializable report."""

    dataset_path = Path(dataset_path)
    checkpoint_path = Path(checkpoint_path)
    with np.load(dataset_path, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    missing = sorted(set(REQUIRED_KEYS) - set(data))
    if missing:
        raise ValueError(f"dataset missing keys: {missing}")
    rows = len(data["option_id"])
    if any(len(data[key]) != rows for key in REQUIRED_KEYS):
        raise ValueError("dataset arrays do not share one row count")

    checkpoint_payload = serialization.msgpack_restore(checkpoint_path.read_bytes())
    if not isinstance(checkpoint_payload, Mapping):
        raise ValueError("checkpoint payload must be a mapping")
    prediction_fn = predictor or teacher_forced_predictions
    predictions = prediction_fn(data, checkpoint_payload, batch_size)
    return build_report(
        data, predictions, dataset_path, checkpoint_path, checkpoint_payload
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_checkpoint(args.dataset, args.checkpoint, args.batch_size)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
