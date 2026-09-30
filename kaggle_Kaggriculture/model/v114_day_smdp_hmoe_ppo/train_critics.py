"""Train and qualify V114 manager/option critics with JAX."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import tempfile
from typing import Any

import jax
import jax.numpy as jnp
import numpy as np
import optax
from scipy.stats import rankdata, spearmanr

from critics import ManagerCritic, OptionCritic, serialize_parameters


def _tree_to_jax(tree):
    return jax.tree_util.tree_map(lambda value: jnp.asarray(value), tree)


def _tree_to_numpy(tree):
    return jax.tree_util.tree_map(lambda value: np.asarray(value), tree)


def _mlp(params, inputs, activate_final=False):
    result = inputs
    for index in range(len(params)):
        layer = params[f"layer_{index}"]
        result = result @ layer["weight"] + layer["bias"]
        if activate_final or index + 1 < len(params):
            result = jnp.tanh(result)
    return result


def _forward(params, inputs):
    latent = _mlp(params["trunk"], inputs, True)
    return (
        _mlp(params["value_head"], latent)[:, 0],
        _mlp(params["margin_head"], latent)[:, 0],
        _mlp(params["catastrophe_head"], latent)[:, 0],
    )


def _loss(params, batch, positive_weight, ranking_weight):
    value, margin, catastrophe_logit = _forward(params, batch["x"])
    value_loss = jnp.mean(jnp.square(value - batch["value"]))
    margin_loss = jnp.mean(jnp.square(margin - batch["margin"]))
    labels = batch["catastrophe"]
    weights = jnp.where(labels > 0.5, positive_weight, 1.0)
    catastrophe_loss = jnp.mean(weights * optax.sigmoid_binary_cross_entropy(catastrophe_logit, labels))
    left = _forward(params, batch["pair_x_left"])[0]
    right = _forward(params, batch["pair_x_right"])[0]
    ranking_loss = jnp.mean(jax.nn.softplus(-batch["pair_sign"] * (left - right)))
    return value_loss + 0.5 * margin_loss + 0.5 * catastrophe_loss + ranking_weight * ranking_loss


def _auc(labels, scores) -> float:
    labels = np.asarray(labels) > 0.5
    positives, negatives = int(labels.sum()), int((~labels).sum())
    if positives == 0 or negatives == 0:
        return float("nan")
    ranks = rankdata(np.asarray(scores), method="average")
    return float((ranks[labels].sum() - positives * (positives + 1) / 2) / (positives * negatives))


def _ece(labels, probabilities, bins=10) -> float:
    labels, probabilities = np.asarray(labels), np.asarray(probabilities)
    result = 0.0
    for lower in np.linspace(0.0, 1.0, bins, endpoint=False):
        upper = lower + 1.0 / bins
        mask = (probabilities >= lower) & (probabilities < upper if upper < 1 else probabilities <= upper)
        if mask.any():
            result += mask.mean() * abs(probabilities[mask].mean() - labels[mask].mean())
    return float(result)


def _direction_accuracy(episode_id, step, seat, target, prediction) -> float:
    groups: dict[tuple[int, int], dict[int, tuple[float, float]]] = {}
    for episode, turn, player, truth, estimate in zip(episode_id, step, seat, target, prediction):
        groups.setdefault((int(episode), int(turn)), {})[int(player)] = (float(truth), float(estimate))
    outcomes = []
    for pair in groups.values():
        if set(pair) != {0, 1} or pair[0][0] == pair[1][0]:
            continue
        outcomes.append(np.sign(pair[0][0] - pair[1][0]) == np.sign(pair[0][1] - pair[1][1]))
    return float(np.mean(outcomes)) if outcomes else float("nan")


def _metrics(params, x, value, margin, catastrophe, episode_id, step, seat, train_value_mean):
    pred_value, pred_margin, logits = _forward(_tree_to_jax(params), jnp.asarray(x))
    pred_value, pred_margin, logits = map(np.asarray, (pred_value, pred_margin, logits))
    probability = 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))
    rho = spearmanr(value, pred_value).statistic
    return {
        "rows": int(len(x)),
        "value_mae": float(np.mean(np.abs(pred_value - value))),
        "constant_baseline_mae": float(np.mean(np.abs(train_value_mean - value))),
        "value_spearman": float(rho) if np.isfinite(rho) else float("nan"),
        "margin_mae": float(np.mean(np.abs(pred_margin - margin))),
        "catastrophe_auroc": _auc(catastrophe, probability),
        "catastrophe_brier": float(np.mean(np.square(probability - catastrophe))),
        "catastrophe_ece": _ece(catastrophe, probability),
        "paired_direction_accuracy": _direction_accuracy(episode_id, step, seat, value, pred_value),
    }


def _pair_indexes(episode_id, step, seat, target, mask):
    groups: dict[tuple[int, int], dict[int, int]] = {}
    for index in np.flatnonzero(mask):
        groups.setdefault((int(episode_id[index]), int(step[index])), {})[int(seat[index])] = int(index)
    pairs = []
    for players in groups.values():
        if set(players) != {0, 1}:
            continue
        left, right = players[0], players[1]
        difference = float(target[left] - target[right])
        if difference:
            pairs.append((left, right, np.sign(difference)))
    if not pairs:
        raise ValueError("no dual-seat ranking pairs in split")
    return np.asarray(pairs, dtype=np.float64)


def train_one(
    kind: str, x, value, margin, catastrophe, split, episode_id, step, seat,
    *, seed: int, epochs: int, batch_size: int,
):
    train_mask, validation_mask, test_mask = split == 0, split == 1, split == 2
    mean = x[train_mask].mean(axis=0)
    std = x[train_mask].std(axis=0)
    std[std < 1e-5] = 1.0
    normalized = (x - mean) / std
    critic_class = ManagerCritic if kind == "manager" else OptionCritic
    critic = critic_class(x.shape[1], hidden_dims=(128, 64), seed=seed, value_coef=0.5)
    params = _tree_to_jax(critic.state_dict())
    optimizer = optax.chain(optax.clip_by_global_norm(1.0), optax.adam(3e-4))
    state = optimizer.init(params)
    positive_rate = float(catastrophe[train_mask].mean())
    positive_weight = float((1.0 - positive_rate) / max(positive_rate, 1e-4))
    ranking_weight = 1.0 if kind == "manager" else 0.20
    train_pairs = _pair_indexes(episode_id, step, seat, value, train_mask)
    validation_pairs = _pair_indexes(episode_id, step, seat, value, validation_mask)

    @jax.jit
    def update(current, opt_state, batch):
        loss, gradients = jax.value_and_grad(_loss)(
            current, batch, positive_weight, ranking_weight
        )
        updates, opt_state = optimizer.update(gradients, opt_state, current)
        return optax.apply_updates(current, updates), opt_state, loss

    rng = np.random.default_rng(seed)
    train_indexes = np.flatnonzero(train_mask)
    best_params, best_loss, best_epoch = copy.deepcopy(params), float("inf"), -1
    patience = 15
    history = []
    for epoch in range(epochs):
        rng.shuffle(train_indexes)
        losses = []
        for offset in range(0, len(train_indexes), batch_size):
            indexes = train_indexes[offset:offset + batch_size]
            pair_rows = train_pairs[rng.integers(0, len(train_pairs), size=max(64, len(indexes) // 2))]
            pair_left = pair_rows[:, 0].astype(np.int64)
            pair_right = pair_rows[:, 1].astype(np.int64)
            batch = {
                "x": jnp.asarray(normalized[indexes]),
                "value": jnp.asarray(value[indexes]),
                "margin": jnp.asarray(margin[indexes]),
                "catastrophe": jnp.asarray(catastrophe[indexes]),
                "pair_x_left": jnp.asarray(normalized[pair_left]),
                "pair_x_right": jnp.asarray(normalized[pair_right]),
                "pair_sign": jnp.asarray(pair_rows[:, 2], dtype=jnp.float32),
            }
            params, state, loss = update(params, state, batch)
            losses.append(float(loss))
        validation_batch = {
            "x": jnp.asarray(normalized[validation_mask]),
            "value": jnp.asarray(value[validation_mask]),
            "margin": jnp.asarray(margin[validation_mask]),
            "catastrophe": jnp.asarray(catastrophe[validation_mask]),
            "pair_x_left": jnp.asarray(normalized[validation_pairs[:, 0].astype(np.int64)]),
            "pair_x_right": jnp.asarray(normalized[validation_pairs[:, 1].astype(np.int64)]),
            "pair_sign": jnp.asarray(validation_pairs[:, 2], dtype=jnp.float32),
        }
        validation_loss = float(_loss(params, validation_batch, positive_weight, ranking_weight))
        history.append({"epoch": epoch + 1, "train_loss": float(np.mean(losses)), "validation_loss": validation_loss})
        if validation_loss < best_loss - 1e-6:
            best_params, best_loss, best_epoch = copy.deepcopy(params), validation_loss, epoch + 1
        elif epoch + 1 - best_epoch >= patience:
            break
    return _tree_to_numpy(best_params), mean.astype(np.float32), std.astype(np.float32), history, {
        "best_epoch": best_epoch,
        "best_validation_loss": best_loss,
        "positive_rate_train": positive_rate,
        "ranking_weight": ranking_weight,
        "train_ranking_pairs": int(len(train_pairs)),
        "validation_ranking_pairs": int(len(validation_pairs)),
        "test_mask": test_mask,
        "normalized": normalized,
        "train_value_mean": float(value[train_mask].mean()),
    }


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2, allow_nan=False)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=512)
    args = parser.parse_args()
    data = np.load(args.dataset, allow_pickle=False)
    x = np.asarray(data["features"], dtype=np.float32)
    split = np.asarray(data["split"])
    catastrophe = np.asarray(data["catastrophe"], dtype=np.float32)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reports = {}
    for kind, value in (("manager", data["manager_own"]), ("option", data["option_value"])):
        params, mean, std, history, info = train_one(
            kind, x, np.asarray(value, dtype=np.float32), np.asarray(data["manager_margin"], dtype=np.float32),
            catastrophe, split, data["episode_id"], data["step"], data["seat"],
            seed=114200 if kind == "manager" else 114201,
            epochs=args.epochs, batch_size=args.batch_size,
        )
        (args.output_dir / f"{kind}_critic.npz").write_bytes(serialize_parameters(params))
        np.savez_compressed(args.output_dir / f"{kind}_normalizer.npz", mean=mean, std=std)
        mask = info.pop("test_mask")
        normalized = info.pop("normalized")
        metrics = _metrics(
            params, normalized[mask], np.asarray(value)[mask], data["manager_margin"][mask],
            catastrophe[mask], data["episode_id"][mask], data["step"][mask], data["seat"][mask],
            info["train_value_mean"],
        )
        reports[kind] = {**info, "metrics": metrics, "history": history}
    manager = reports["manager"]["metrics"]
    option = reports["option"]["metrics"]
    manager_passed = (
        manager["value_mae"] < manager["constant_baseline_mae"]
        and manager["value_spearman"] >= 0.50
        and manager["catastrophe_auroc"] >= 0.75
        and manager["paired_direction_accuracy"] >= 0.65
    )
    option_passed = option["value_mae"] < option["constant_baseline_mae"] and option["value_spearman"] >= 0.30
    report = {
        "schema": "kaggriculture-v114-critic-pretrain-v1",
        "model_id": "v114_day_smdp_hmoe_ppo",
        "dataset": str(args.dataset),
        "jax_version": jax.__version__,
        "devices": [str(device) for device in jax.devices()],
        "value_coefficient": 0.5,
        "manager": reports["manager"],
        "option": reports["option"],
        "residual": {"status": "NOT_TRAINED_PAIRED_COUNTERFACTUAL_REQUIRED", "gate_passed": False},
        "manager_gate_passed": bool(manager_passed),
        "option_gate_passed": bool(option_passed),
        "v4_1_gate_passed": False,
        "decision": "CONTINUE_TO_PAIRED_RESIDUAL_COUNTERFACTUAL" if manager_passed and option_passed else "REVISE_CRITIC_REPRESENTATION_WITHIN_V4",
    }
    _atomic_json(args.output_dir / "training_report.json", report)
    print(json.dumps({
        "manager_gate_passed": report["manager_gate_passed"],
        "option_gate_passed": report["option_gate_passed"],
        "v4_1_gate_passed": report["v4_1_gate_passed"],
        "manager_metrics": manager,
        "option_metrics": option,
        "decision": report["decision"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
