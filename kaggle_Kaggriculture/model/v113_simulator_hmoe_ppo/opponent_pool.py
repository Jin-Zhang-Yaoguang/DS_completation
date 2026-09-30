"""Reproducible stratified opponent league for V113 PPO rollouts."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from collect_rollouts import resolve_opponent
from opponent_factory import checkpoint_opponent


LAYER_IDS = {
    "gold_train": 0,
    "ppo_history": 1,
    "self_play": 2,
    "exploiter": 3,
    "anchor": 4,
}


@dataclass(frozen=True)
class PoolAssignment:
    seed: int
    layer: str
    layer_id: int
    member_id: str
    member_index: int
    member: dict[str, Any]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_path(registry_path: Path, registry: dict[str, Any], value: str) -> Path:
    base = (registry_path.parent / registry.get("path_base", ".")).resolve()
    return (base / value).resolve()


def load_registry(path: Path, verify_hashes: bool = True) -> dict[str, Any]:
    path = path.resolve()
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("schema") != "kaggriculture-v113-opponent-registry-v1":
        raise ValueError("unsupported opponent registry schema")
    target = registry["training_layer_weights"]
    if set(target) != set(LAYER_IDS):
        raise ValueError(f"training layers must be exactly {sorted(LAYER_IDS)}")
    if not np.isclose(sum(float(value) for value in target.values()), 1.0):
        raise ValueError("training layer weights must sum to one")
    members = registry["members"]
    member_ids = [member["id"] for member in members]
    if len(member_ids) != len(set(member_ids)):
        raise ValueError("opponent member ids must be unique")
    training_members = defaultdict(list)
    seen_hashes: dict[str, str] = {}
    for index, member in enumerate(members):
        member["member_index"] = index
        layer = member.get("training_layer")
        if layer is not None:
            if layer not in LAYER_IDS:
                raise ValueError(f"unknown training layer for {member['id']}: {layer}")
            if not member.get("training_enabled", False):
                raise ValueError(f"training member is disabled: {member['id']}")
            if float(member.get("sampling_weight", 0.0)) <= 0:
                raise ValueError(f"training member has no positive weight: {member['id']}")
            training_members[layer].append(member)
        if member["kind"] in {"agent", "checkpoint"}:
            resolved = _resolve_path(path, registry, member["path"])
            if not resolved.is_file():
                raise FileNotFoundError(f"missing opponent artifact: {resolved}")
            member["resolved_path"] = str(resolved)
            actual = sha256_file(resolved)
            if verify_hashes and actual != member.get("sha256"):
                raise ValueError(
                    f"SHA256 mismatch for {member['id']}: {actual} != {member.get('sha256')}"
                )
            if actual in seen_hashes:
                raise ValueError(
                    f"duplicate opponent artifact behavior proxy: {member['id']} and {seen_hashes[actual]}"
                )
            seen_hashes[actual] = member["id"]
    for layer in LAYER_IDS:
        if not training_members[layer]:
            raise ValueError(f"training layer has no members: {layer}")
        total = sum(float(member["sampling_weight"]) for member in training_members[layer])
        if not np.isclose(total, 1.0):
            raise ValueError(f"member weights for {layer} must sum to one, got {total}")

    gold_families = defaultdict(set)
    for member in members:
        split = member.get("gold_split")
        if split:
            gold_families[split].add(member["behavior_family"])
    expected = {"train", "dev", "blind"}
    if set(gold_families) != expected:
        raise ValueError("gold registry must contain train/dev/blind splits")
    family_count = sum(len(value) for value in gold_families.values())
    split_ratios = {key: len(value) / family_count for key, value in gold_families.items()}
    if split_ratios != {"train": 0.6, "dev": 0.2, "blind": 0.2}:
        raise ValueError(f"gold behavior-family split must be 60/20/20, got {split_ratios}")
    registry["registry_path"] = str(path)
    registry["registry_sha256"] = sha256_file(path)
    registry["gold_family_split_ratios"] = split_ratios
    return registry


def _largest_remainder(total: int, weighted_ids: list[tuple[str, float]]) -> dict[str, int]:
    raw = {key: total * float(weight) for key, weight in weighted_ids}
    result = {key: int(np.floor(value)) for key, value in raw.items()}
    remaining = total - sum(result.values())
    order = sorted(
        weighted_ids,
        key=lambda item: (-(raw[item[0]] - result[item[0]]), item[0]),
    )
    for key, _ in order[:remaining]:
        result[key] += 1
    return result


def layer_quotas(registry: dict[str, Any], seeds: int) -> dict[str, int]:
    if seeds <= 0:
        raise ValueError("seeds must be positive")
    if seeds == 64 and registry.get("iteration_seed_quotas_64"):
        quotas = {key: int(value) for key, value in registry["iteration_seed_quotas_64"].items()}
        if set(quotas) != set(LAYER_IDS) or sum(quotas.values()) != seeds:
            raise ValueError("invalid 64-seed quota override")
        return quotas
    return _largest_remainder(
        seeds,
        [(key, float(registry["training_layer_weights"][key])) for key in LAYER_IDS],
    )


def _member_weights(
    members: list[dict[str, Any]], stats: dict[str, Any] | None,
) -> list[tuple[str, float]]:
    weighted = []
    stat_members = (stats or {}).get("members", {})
    for member in members:
        weight = float(member["sampling_weight"])
        row = stat_members.get(member["id"], {})
        score = row.get("candidate_score_rate")
        if score is not None and member.get("sampling_policy") == "pfsp":
            # Standard hard-opponent PFSP: retain a floor while prioritizing opponents
            # the current candidate does not yet beat reliably.
            weight *= 0.10 + (1.0 - float(score)) ** 2
        progress = row.get("absolute_learning_progress")
        if progress is not None and member.get("sampling_policy") == "learning_progress":
            weight *= 0.25 + float(progress)
        weighted.append((member["id"], weight))
    normalizer = sum(value for _, value in weighted)
    return [(key, value / normalizer) for key, value in weighted]


def build_schedule(
    registry: dict[str, Any], seed_start: int, seeds: int, pool_seed: int,
    iteration: int = 0, stats: dict[str, Any] | None = None,
) -> list[PoolAssignment]:
    quotas = layer_quotas(registry, seeds)
    rng = np.random.default_rng(int(pool_seed) + 1_000_003 * int(iteration))
    members_by_layer = {
        layer: [
            member for member in registry["members"]
            if member.get("training_enabled") and member.get("training_layer") == layer
        ]
        for layer in LAYER_IDS
    }
    layer_slots = [layer for layer in LAYER_IDS for _ in range(quotas[layer])]
    rng.shuffle(layer_slots)
    member_slots: dict[str, list[dict[str, Any]]] = {}
    for layer, count in quotas.items():
        members = members_by_layer[layer]
        by_id = {member["id"]: member for member in members}
        counts = _largest_remainder(count, _member_weights(members, stats))
        slots = [by_id[member_id] for member_id, amount in counts.items() for _ in range(amount)]
        rng.shuffle(slots)
        member_slots[layer] = slots
    assignments = []
    offsets = Counter()
    for index, layer in enumerate(layer_slots):
        member = member_slots[layer][offsets[layer]]
        offsets[layer] += 1
        assignments.append(PoolAssignment(
            seed=int(seed_start + index), layer=layer, layer_id=LAYER_IDS[layer],
            member_id=member["id"], member_index=int(member["member_index"]), member=member,
        ))
    return assignments


def build_opponent(
    assignment: PoolAssignment, unique_name: str,
):
    member = assignment.member
    if member["kind"] == "builtin":
        return resolve_opponent(member["spec"], unique_name)
    if member["kind"] == "agent":
        return resolve_opponent(member["resolved_path"], unique_name)
    if member["kind"] == "checkpoint":
        return checkpoint_opponent(
            Path(member["resolved_path"]), member["architecture"],
            member.get("forced_unit_expert"), member.get("forced_market_expert"),
            unit_expert_schedule=member.get("unit_expert_schedule"),
            market_expert_schedule=member.get("market_expert_schedule"),
        )
    raise ValueError(f"unsupported opponent kind: {member['kind']}")


def schedule_report(
    registry: dict[str, Any], assignments: list[PoolAssignment], iteration: int,
    pool_seed: int,
) -> dict[str, Any]:
    layer_counts = Counter(assignment.layer for assignment in assignments)
    member_counts = Counter(assignment.member_id for assignment in assignments)
    total = len(assignments)
    return {
        "schema": "kaggriculture-v113-opponent-schedule-v1",
        "registry_path": registry["registry_path"],
        "registry_sha256": registry["registry_sha256"],
        "iteration": int(iteration),
        "pool_seed": int(pool_seed),
        "seed_groups": total,
        "games": 2 * total,
        "dual_seat_same_opponent": True,
        "target_layer_weights": registry["training_layer_weights"],
        "realized_layer_seed_counts": dict(layer_counts),
        "realized_layer_weights": {
            layer: layer_counts[layer] / total for layer in LAYER_IDS
        },
        "realized_member_seed_counts": dict(member_counts),
        "assignments": [
            {
                "seed": assignment.seed,
                "layer": assignment.layer,
                "member_id": assignment.member_id,
                "member_sha256": assignment.member.get("sha256"),
            }
            for assignment in assignments
        ],
    }
