"""Build full-information route contexts from four-route simulator reports."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from flax import serialization
import jax.numpy as jnp
import numpy as np

from event_program_features import (
    DECISION_HEAD_VALUES,
    FEATURE_SCHEMA,
    MANAGER_FEATURE_DIM,
    encode_event_program_features,
)
from model_event_program_ppo import EventProgramPPOManager, validate_checkpoint_metadata
from policy_trainable_event_program import qualified_macro_action_masks
from collect_event_program_ppo_rollouts import atomic_npz
from train_event_program_ppo import atomic_json, file_sha256


SCHEMA = "kaggriculture-v114-counterfactual-route-dataset-v2"
ROUTES = ("WHEAT", "TOMATO", "STRAWBERRY", "MELON")
ROUTE_INDEX = {
    str(value.value): index
    for index, value in enumerate(DECISION_HEAD_VALUES["production_line"])
}


def parse_bindings(values: Sequence[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError("--report requires layer/member=JSON")
        key, value = raw.split("=", 1)
        if key.count("/") != 1:
            raise ValueError("--report requires layer/member=JSON")
        if key in result:
            raise ValueError(f"duplicate report binding: {key}")
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"missing report: {path}")
        result[key] = path
    if not result:
        raise ValueError("at least one report is required")
    return result


def _initial_observation(seed: int, seat: int) -> dict[str, Any]:
    from kaggle_environments import make

    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    observation = dict(env.state[int(seat)].observation)
    observation["step"] = 0
    observation["day"] = 0
    observation["hour"] = 0
    observation["player"] = int(seat)
    return observation


def _context_rows(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    if report.get("status") != "VALID":
        raise ValueError("counterfactual source report is not VALID")
    grouped: dict[tuple[int, int], dict[str, Mapping[str, Any]]] = {}
    for row in report.get("rows", []):
        if row.get("error") is not None or row.get("statuses") != ["DONE", "DONE"]:
            raise ValueError("source report contains an invalid game")
        key = (int(row["seed"]), int(row["seat"]))
        route = str(row["decision_name"])
        if route not in ROUTES or route in grouped.setdefault(key, {}):
            raise ValueError("duplicate or unsupported route in context")
        grouped[key][route] = row
    contexts: list[dict[str, Any]] = []
    for (seed, seat), routes in sorted(grouped.items()):
        if set(routes) != set(ROUTES):
            raise ValueError(f"context {seed}/{seat} does not have all four routes")
        opponent_ids = {str(row["opponent_id"]) for row in routes.values()}
        if len(opponent_ids) != 1:
            raise ValueError("opponent differs within one counterfactual context")
        contexts.append({
            "seed": seed,
            "seat": seat,
            "opponent_id": next(iter(opponent_ids)),
            "routes": routes,
        })
    return contexts


def build(args: argparse.Namespace) -> dict[str, Any]:
    bindings = parse_bindings(args.report)
    checkpoint = Path(args.checkpoint).expanduser().resolve()
    payload = serialization.msgpack_restore(checkpoint.read_bytes())
    validate_checkpoint_metadata(payload)
    if payload.get("feature_schema") != FEATURE_SCHEMA:
        raise ValueError("checkpoint feature schema mismatch")
    model = EventProgramPPOManager()

    records: list[dict[str, Any]] = []
    report_shas: dict[str, str] = {}
    for binding, path in bindings.items():
        layer, member = binding.split("/", 1)
        source = json.loads(path.read_text(encoding="utf-8"))
        report_shas[binding] = file_sha256(path)
        for context in _context_rows(source):
            if bool(args.delayed_features):
                route_features = [
                    np.asarray(context["routes"][route].get("probe_features"), dtype=np.float32)
                    for route in ROUTES
                ]
                if any(vector.shape != (MANAGER_FEATURE_DIM,) for vector in route_features):
                    raise ValueError("delayed report is missing a 427-value probe feature vector")
                if not all(np.array_equal(route_features[0], vector) for vector in route_features[1:]):
                    raise ValueError("route-specific leakage detected in delayed context features")
                features = route_features[0]
                observation = None
            else:
                observation = _initial_observation(context["seed"], context["seat"])
                features = encode_event_program_features(
                    observation, current_decision=None, current_event="DAY_BOUNDARY"
                )
                second = encode_event_program_features(
                    observation, current_decision=None, current_event="DAY_BOUNDARY"
                )
                if not np.array_equal(features, second):
                    raise ValueError("initial feature encoding is not deterministic")
            candidate = np.full(5, np.nan, dtype=np.float32)
            opponent = np.full(5, np.nan, dtype=np.float32)
            score = np.full(5, np.nan, dtype=np.float32)
            catastrophe = np.zeros(5, dtype=np.bool_)
            route_valid = np.zeros(5, dtype=np.bool_)
            for route, row in context["routes"].items():
                index = ROUTE_INDEX[route]
                candidate[index] = float(row["candidate_reward"])
                opponent[index] = float(row["opponent_reward"])
                score[index] = float(row["score"])
                catastrophe[index] = bool(row["catastrophe"])
                route_valid[index] = True
            mask = (
                route_valid.copy()
                if bool(args.delayed_features)
                else qualified_macro_action_masks(observation)["production_line"][0]
            )
            if not np.array_equal(route_valid, mask):
                raise ValueError("four-route validity differs from production action mask")
            records.append({
                **context,
                "layer": layer,
                "member": member,
                "features": np.asarray(features, dtype=np.float32),
                "mask": np.asarray(mask, dtype=np.bool_),
                "candidate_reward": candidate,
                "opponent_reward": opponent,
                "score": score,
                "catastrophe": catastrophe,
                "route_valid": route_valid,
            })

    records.sort(key=lambda row: (row["layer"], row["member"], row["seed"], row["seat"]))
    features = np.asarray([row["features"] for row in records], dtype=np.float32)
    outputs = model.apply({"params": payload["params"]}, jnp.asarray(features))
    old_logits = np.asarray(outputs["actor_logits"]["production_line"], dtype=np.float32)
    arrays = {
        "features": features,
        "mask_production_line": np.asarray([row["mask"] for row in records], dtype=np.bool_),
        "old_logits_production_line": old_logits,
        "candidate_reward": np.asarray([row["candidate_reward"] for row in records]),
        "opponent_reward": np.asarray([row["opponent_reward"] for row in records]),
        "score": np.asarray([row["score"] for row in records]),
        "catastrophe": np.asarray([row["catastrophe"] for row in records]),
        "route_valid": np.asarray([row["route_valid"] for row in records]),
        "seed": np.asarray([row["seed"] for row in records], dtype=np.int64),
        "seat": np.asarray([row["seat"] for row in records], dtype=np.int8),
        "layer": np.asarray([row["layer"] for row in records]),
        "member": np.asarray([row["member"] for row in records]),
        "opponent_id": np.asarray([row["opponent_id"] for row in records]),
    }
    expected_contexts = int(args.expected_contexts)
    if features.shape != (expected_contexts, MANAGER_FEATURE_DIM):
        raise ValueError(
            f"expected {expected_contexts}x{MANAGER_FEATURE_DIM} contexts, got {features.shape}"
        )
    output = Path(args.output).expanduser().resolve()
    atomic_npz(output, arrays)
    outcome = np.where(arrays["score"] == 1.0, 1.0, np.where(arrays["score"] == 0.5, 0.0, -1.0))
    relative = 2.0 * arrays["candidate_reward"] / np.maximum(
        arrays["candidate_reward"] + arrays["opponent_reward"], 1.0
    ) - 1.0
    economy = 0.1 * np.tanh((arrays["candidate_reward"] - 3000.0) / 10000.0)
    utility = outcome + relative + economy - arrays["catastrophe"].astype(np.float32)
    utility = np.where(arrays["mask_production_line"], utility, 0.0)
    masked_logits = np.where(arrays["mask_production_line"], old_logits, -np.inf)
    shifted = masked_logits - np.max(masked_logits, axis=1, keepdims=True)
    old_probability = np.exp(shifted)
    old_probability /= np.sum(old_probability, axis=1, keepdims=True)
    expected_old_utility = np.sum(old_probability * utility, axis=1)
    oracle_utility = np.max(np.where(arrays["mask_production_line"], utility, -np.inf), axis=1)
    oracle_gain = oracle_utility - expected_old_utility
    best_own = np.nanargmax(
        np.where(arrays["mask_production_line"], arrays["candidate_reward"], np.nan),
        axis=1,
    )
    best = np.nanargmax(np.where(arrays["mask_production_line"], utility, np.nan), axis=1)
    own_counts = {
        str(DECISION_HEAD_VALUES["production_line"][i].value): int(np.sum(best_own == i))
        for i in range(5)
    }
    counts = {
        str(DECISION_HEAD_VALUES["production_line"][i].value): int(np.sum(best == i))
        for i in range(5)
    }
    non_dominant_rate = 1.0 - max(counts.values()) / len(best)
    counterfactual_gate = {
        "contexts_with_positive_oracle_gain_rate": float(np.mean(oracle_gain > 1.0e-9)),
        "contexts_with_positive_oracle_gain_min_rate": 0.20,
        "mean_oracle_utility_gain": float(np.mean(oracle_gain)),
        "mean_oracle_utility_gain_min": 0.01,
        "best_route_non_dominant_rate": float(non_dominant_rate),
        "best_route_not_single_class_rate_min": 0.05,
    }
    counterfactual_gate["passed"] = bool(
        counterfactual_gate["contexts_with_positive_oracle_gain_rate"]
        >= counterfactual_gate["contexts_with_positive_oracle_gain_min_rate"]
        and counterfactual_gate["mean_oracle_utility_gain"]
        >= counterfactual_gate["mean_oracle_utility_gain_min"]
        and counterfactual_gate["best_route_non_dominant_rate"]
        >= counterfactual_gate["best_route_not_single_class_rate_min"]
    )
    report = {
        "schema": SCHEMA,
        "status": "PASS_COUNTERFACTUAL_GATE" if counterfactual_gate["passed"] else "REJECT_COUNTERFACTUAL_GATE",
        "source_validation": "VALID",
        "feature_time": "step_24_after_common_probe" if bool(args.delayed_features) else "step_0",
        "contexts": len(records),
        "games": len(records) * 4,
        "features": list(features.shape),
        "checkpoint": {"path": str(checkpoint), "sha256": file_sha256(checkpoint)},
        "source_reports": {key: {"path": str(bindings[key]), "sha256": report_shas[key]} for key in bindings},
        "best_own_reward_route_counts": own_counts,
        "best_utility_route_counts": counts,
        "counterfactual_gate": counterfactual_gate,
        "artifact": {"path": str(output), "sha256": file_sha256(output)},
    }
    atomic_json(Path(args.output_report).expanduser().resolve(), report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--report", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--delayed-features", action="store_true")
    parser.add_argument("--expected-contexts", type=int, default=128)
    return parser


if __name__ == "__main__":
    print(json.dumps(build(build_parser().parse_args()), indent=2, ensure_ascii=False))
