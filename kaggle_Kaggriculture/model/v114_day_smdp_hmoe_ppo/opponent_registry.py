"""V114 V4-0 dynamic opponent league with reproducible dual-seat schedules.

The registry is an immutable identity manifest.  Runtime statistics influence
PFSP weights, but never change member identity, SHA, split, or lineage.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import re
import tarfile
from typing import Any, Iterable, Mapping


LAYER_ORDER = (
    "gold_train",
    "ppo_history",
    "self_play",
    "exploiter",
    "anchor",
)

STAGE_WEIGHTS: dict[str, dict[str, float]] = {
    "survival": {
        "gold_train": 0.15,
        "ppo_history": 0.35,
        "self_play": 0.10,
        "exploiter": 0.05,
        "anchor": 0.35,
    },
    "improvement": {
        "gold_train": 0.30,
        "ppo_history": 0.35,
        "self_play": 0.15,
        "exploiter": 0.10,
        "anchor": 0.10,
    },
    "final": {
        "gold_train": 0.40,
        "ppo_history": 0.30,
        "self_play": 0.15,
        "exploiter": 0.10,
        "anchor": 0.05,
    },
}

STAGE_ALIASES = {
    "survival": "survival",
    "improvement": "improvement",
    "final": "final",
    "final_league": "final",
}

SCHEMA = "kaggriculture-v114-opponent-registry-v1"
MAX_MEMBER_RATIO = 0.125
MAX_V76_RATIO = 0.10
MAX_HISTORY_MILESTONES = 12
HARD_GOLD_MIN_TOTAL_RATIO = 0.10
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SeedAssignment:
    """One environment seed block; both candidate seats use this opponent."""

    seed: int
    layer: str
    opponent_id: str
    opponent_sha256: str
    role: str
    lineage: str
    behavior_family: str


@dataclass(frozen=True)
class GameAssignment:
    seed: int
    candidate_seat: int
    opponent_seat: int
    layer: str
    opponent_id: str
    opponent_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def builtin_sha256(spec: str) -> str:
    """Stable identity hash for a versioned built-in opponent spec."""

    return hashlib.sha256(spec.encode("utf-8")).hexdigest()


def sha256_tar_member(archive: Path, member_name: str) -> str:
    with tarfile.open(archive, "r:gz") as source:
        member = source.getmember(member_name)
        stream = source.extractfile(member)
        if stream is None:
            raise ValueError(f"archive member is not a regular file: {member_name}")
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
        return digest.hexdigest()


def _resolve_path(registry_path: Path, registry: Mapping[str, Any], value: str) -> Path:
    base = (registry_path.parent / str(registry.get("path_base", "."))).resolve()
    return (base / value).resolve()


def _normalise_stage(stage: str) -> str:
    try:
        return STAGE_ALIASES[stage]
    except KeyError as exc:
        raise ValueError(f"unknown league stage: {stage!r}") from exc


def _validate_exact_stage_weights(stages: Mapping[str, Any]) -> None:
    if set(stages) != set(STAGE_WEIGHTS):
        raise ValueError(f"stages must be exactly {sorted(STAGE_WEIGHTS)}")
    for stage, expected in STAGE_WEIGHTS.items():
        actual = stages[stage]
        if set(actual) != set(LAYER_ORDER):
            raise ValueError(f"{stage} layers must be exactly {list(LAYER_ORDER)}")
        for layer in LAYER_ORDER:
            if not math.isclose(float(actual[layer]), expected[layer], abs_tol=1e-12):
                raise ValueError(
                    f"{stage}.{layer} must be {expected[layer]}, got {actual[layer]}"
                )
        if not math.isclose(sum(float(actual[key]) for key in LAYER_ORDER), 1.0):
            raise ValueError(f"{stage} weights must sum to one")


def _validate_foundation_l1(
    registry_path: Path,
    registry: Mapping[str, Any],
    members_by_id: Mapping[str, Mapping[str, Any]],
    *,
    verify_artifacts: bool,
) -> None:
    contract = registry.get("foundation_l1")
    if not isinstance(contract, Mapping):
        raise ValueError("foundation_l1 contract is required")
    representative_ids = list(contract.get("representative_ids", []))
    if len(representative_ids) != 4 or len(set(representative_ids)) != 4:
        raise ValueError("foundation_l1 must freeze exactly four unique representatives")
    if int(contract.get("fresh_seed_blocks_total", 0)) != 32:
        raise ValueError("foundation_l1 requires exactly 32 fresh seed blocks")
    if int(contract.get("fresh_seed_blocks_per_representative", 0)) != 8:
        raise ValueError("foundation_l1 requires eight seed blocks per representative")
    if contract.get("dual_seat_same_opponent") is not True:
        raise ValueError("foundation_l1 must use the same opponent for both seats")

    total_weight = 0.0
    for member_id in representative_ids:
        member = members_by_id.get(member_id)
        if member is None:
            raise ValueError(f"missing foundation_l1 representative: {member_id}")
        if member.get("status") != "FOUNDATION_L1_FIXED_OPPONENT":
            raise ValueError(f"foundation_l1 representative has wrong status: {member_id}")
        if member.get("training_enabled") or member.get("training_layer") is not None:
            raise ValueError(f"foundation_l1 representative may not enter the league: {member_id}")
        weight = float(member.get("foundation_l1_weight", 0.0))
        if not math.isclose(weight, 0.25, abs_tol=1e-12):
            raise ValueError(f"foundation_l1 representative weight must be 0.25: {member_id}")
        total_weight += weight

        package_value = str(member.get("package_path", ""))
        package_sha = str(member.get("package_sha256", ""))
        package_members = member.get("package_members_sha256")
        if not package_value or not _SHA_RE.fullmatch(package_sha):
            raise ValueError(f"foundation_l1 representative lacks frozen package SHA: {member_id}")
        if not isinstance(package_members, Mapping) or not package_members:
            raise ValueError(f"foundation_l1 representative lacks package member SHAs: {member_id}")
        package_path = _resolve_path(registry_path, registry, package_value)
        if not package_path.is_file():
            raise FileNotFoundError(f"missing foundation_l1 package for {member_id}: {package_path}")
        if verify_artifacts and sha256_file(package_path) != package_sha:
            raise ValueError(f"foundation_l1 package SHA256 mismatch: {member_id}")
        if verify_artifacts:
            for name, expected_sha in package_members.items():
                if not _SHA_RE.fullmatch(str(expected_sha)):
                    raise ValueError(f"invalid package member SHA for {member_id}: {name}")
                actual_sha = sha256_tar_member(package_path, str(name))
                if actual_sha != expected_sha:
                    raise ValueError(
                        f"foundation_l1 package member SHA256 mismatch: {member_id}/{name}"
                    )
    if not math.isclose(total_weight, 1.0, abs_tol=1e-12):
        raise ValueError("foundation_l1 representative weights must sum to one")


def load_registry(path: Path | str, verify_artifacts: bool = True) -> dict[str, Any]:
    """Load and fail-closed validate the frozen opponent manifest."""

    registry_path = Path(path).resolve()
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema") != SCHEMA:
        raise ValueError(f"unsupported opponent registry schema: {registry.get('schema')}")
    _validate_exact_stage_weights(registry.get("stage_weights", {}))

    constraints = registry.get("constraints", {})
    expected_constraints = {
        "max_member_total_ratio": MAX_MEMBER_RATIO,
        "max_v76_total_ratio": MAX_V76_RATIO,
        "max_ppo_history_milestones": MAX_HISTORY_MILESTONES,
        "hard_gold_min_total_ratio": HARD_GOLD_MIN_TOTAL_RATIO,
        "dual_seat_same_opponent": True,
    }
    for key, expected in expected_constraints.items():
        actual = constraints.get(key)
        if isinstance(expected, float):
            valid = actual is not None and math.isclose(float(actual), expected, abs_tol=1e-12)
        else:
            valid = actual == expected
        if not valid:
            raise ValueError(f"registry constraint {key} must be {expected!r}, got {actual!r}")

    members = registry.get("members")
    if not isinstance(members, list) or not members:
        raise ValueError("registry members must be a non-empty list")
    ids: set[str] = set()
    members_by_id: dict[str, dict[str, Any]] = {}
    by_layer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    history_count = 0
    for index, member in enumerate(members):
        member_id = str(member.get("id", ""))
        if not member_id or member_id in ids:
            raise ValueError(f"missing or duplicate member id: {member_id!r}")
        ids.add(member_id)
        members_by_id[member_id] = member
        for field in ("kind", "sha256", "role", "lineage", "behavior_family", "status"):
            if not member.get(field):
                raise ValueError(f"{member_id} missing auditable field: {field}")
        if not _SHA_RE.fullmatch(str(member["sha256"])):
            raise ValueError(f"{member_id} has invalid sha256")
        novelty = float(member.get("behavior_novelty", -1.0))
        if not 0.0 <= novelty <= 1.0:
            raise ValueError(f"{member_id} behavior_novelty must be in [0, 1]")

        kind = member["kind"]
        if kind in {"agent", "checkpoint"}:
            if not member.get("path"):
                raise ValueError(f"{member_id} has no artifact path")
            resolved = _resolve_path(registry_path, registry, member["path"])
            if not resolved.is_file():
                raise FileNotFoundError(f"missing opponent artifact for {member_id}: {resolved}")
            actual_sha = sha256_file(resolved)
            if verify_artifacts and actual_sha != member["sha256"]:
                raise ValueError(
                    f"SHA256 mismatch for {member_id}: {actual_sha} != {member['sha256']}"
                )
            member["resolved_path"] = str(resolved)
            if kind == "checkpoint":
                architecture = member.get("architecture")
                if architecture not in {
                    "factorized", "sequence", "timed-sequence", "history-timed-sequence"
                }:
                    raise ValueError(
                        f"checkpoint {member_id} has invalid architecture: {architecture!r}"
                    )
                has_forced = (
                    member.get("forced_unit_expert") is not None
                    and member.get("forced_market_expert") is not None
                )
                has_schedule = (
                    member.get("unit_expert_schedule") is not None
                    and member.get("market_expert_schedule") is not None
                )
                if has_forced == has_schedule:
                    raise ValueError(
                        f"checkpoint {member_id} must define exactly one forced or scheduled expert contract"
                    )
        elif kind == "builtin":
            spec = str(member.get("spec", ""))
            if not spec.startswith("builtin:"):
                raise ValueError(f"{member_id} has invalid builtin spec")
            actual_sha = builtin_sha256(spec)
            if actual_sha != member["sha256"]:
                raise ValueError(
                    f"builtin SHA256 mismatch for {member_id}: {actual_sha} != {member['sha256']}"
                )
        else:
            raise ValueError(f"unsupported member kind for {member_id}: {kind}")

        enabled = bool(member.get("training_enabled", False))
        layer = member.get("training_layer")
        split = member.get("gold_split")
        if split in {"dev", "blind"} and (enabled or layer is not None):
            raise ValueError(f"Gold-{split.title()} member may not be sampled: {member_id}")
        if enabled:
            if layer not in LAYER_ORDER:
                raise ValueError(f"enabled member {member_id} has invalid layer: {layer}")
            if float(member.get("base_weight", 0.0)) <= 0:
                raise ValueError(f"enabled member {member_id} has no positive base_weight")
            if layer == "gold_train" and split != "train":
                raise ValueError(f"Gold-Train member has wrong split: {member_id}")
            if layer != "gold_train" and split is not None:
                raise ValueError(f"non-Gold member has gold_split: {member_id}")
            by_layer[layer].append(member)
            if layer == "ppo_history":
                history_count += 1
        elif layer is not None:
            raise ValueError(f"disabled member still has a training layer: {member_id}")
        member["member_index"] = index

    for layer in LAYER_ORDER:
        if not by_layer[layer]:
            raise ValueError(f"training layer has no members: {layer}")
    if history_count > MAX_HISTORY_MILESTONES:
        raise ValueError(
            f"PPO History has {history_count} milestones; maximum is {MAX_HISTORY_MILESTONES}"
        )
    if not any(member.get("hard_gold") for member in by_layer["gold_train"]):
        raise ValueError("Gold-Train must include at least one hard_gold member")

    _validate_foundation_l1(
        registry_path,
        registry,
        members_by_id,
        verify_artifacts=verify_artifacts,
    )

    result = deepcopy(registry)
    result["registry_path"] = str(registry_path)
    result["registry_sha256"] = sha256_file(registry_path)
    return result


def _largest_remainder(total: int, weights: Mapping[str, float]) -> dict[str, int]:
    raw = {key: total * float(value) for key, value in weights.items()}
    result = {key: int(math.floor(value)) for key, value in raw.items()}
    remaining = total - sum(result.values())
    order_index = {key: index for index, key in enumerate(weights)}
    order = sorted(
        weights,
        key=lambda key: (-(raw[key] - result[key]), order_index[key]),
    )
    for key in order[:remaining]:
        result[key] += 1
    return result


def layer_quotas(stage: str, seed_blocks: int) -> dict[str, int]:
    """Integer quotas using deterministic largest remainder apportionment."""

    if seed_blocks < 8:
        raise ValueError("at least 8 seed blocks are required by the 12.5% member cap")
    stage_name = _normalise_stage(stage)
    return _largest_remainder(seed_blocks, STAGE_WEIGHTS[stage_name])


def _beta_score(row: Mapping[str, Any], prefix: str = "") -> float:
    wins = float(row.get(f"{prefix}wins", 0.0))
    draws = float(row.get(f"{prefix}draws", 0.0))
    losses = float(row.get(f"{prefix}losses", 0.0))
    alpha = float(row.get("beta_alpha", 1.0))
    beta = float(row.get("beta_beta", 1.0))
    games = wins + draws + losses
    return (wins + 0.5 * draws + alpha) / (games + alpha + beta)


def pfsp_components(
    member: Mapping[str, Any], stats: Mapping[str, Any] | None = None,
) -> dict[str, float]:
    """PFSP signal combining smoothed score, progress and behavior novelty."""

    row = stats or {}
    score = _beta_score(row)
    previous_score = _beta_score(row, "previous_") if any(
        key.startswith("previous_") for key in row
    ) else score
    # The main curriculum mass stays around opponents with 30%-70% score rate.
    competence = max(0.05, 1.0 - 2.0 * abs(score - 0.5))
    learning_progress = min(1.0, 4.0 * abs(score - previous_score))
    novelty = float(row.get("behavior_novelty", member.get("behavior_novelty", 0.5)))
    novelty = min(1.0, max(0.0, novelty))
    hardness = 1.0 - score
    combined = (
        0.50 * competence
        + 0.25 * (0.10 + learning_progress)
        + 0.15 * (0.10 + novelty)
        + 0.10 * (0.10 + hardness)
    )
    return {
        "smoothed_score_rate": score,
        "previous_smoothed_score_rate": previous_score,
        "competence": competence,
        "learning_progress": learning_progress,
        "behavior_novelty": novelty,
        "hardness": hardness,
        "combined": combined,
    }


def pfsp_weights(
    members: Iterable[Mapping[str, Any]], stats: Mapping[str, Any] | None = None,
) -> dict[str, float]:
    rows = (stats or {}).get("members", {})
    raw: dict[str, float] = {}
    for member in members:
        components = pfsp_components(member, rows.get(member["id"], {}))
        raw[member["id"]] = float(member["base_weight"]) * components["combined"]
    total = sum(raw.values())
    if total <= 0:
        raise ValueError("PFSP produced no positive opponent weight")
    return {key: value / total for key, value in raw.items()}


def _choose_fair(
    candidates: list[dict[str, Any]],
    counts: Mapping[str, int],
    weights: Mapping[str, float],
) -> dict[str, Any]:
    # Weighted fair allocation: each additional slot goes to the largest
    # weight/(allocated+1).  ID makes ties deterministic.
    return min(
        candidates,
        key=lambda member: (
            -weights[member["id"]] / (counts.get(member["id"], 0) + 1),
            member["id"],
        ),
    )


def _member_caps(members: Iterable[Mapping[str, Any]], seed_blocks: int) -> dict[str, int]:
    general_cap = int(math.floor(seed_blocks * MAX_MEMBER_RATIO + 1e-12))
    v76_cap = int(math.floor(seed_blocks * MAX_V76_RATIO + 1e-12))
    return {
        member["id"]: min(general_cap, v76_cap)
        if member.get("is_v76") else general_cap
        for member in members
    }


def _allocate_layer(
    layer: str,
    quota: int,
    members: list[dict[str, Any]],
    seed_blocks: int,
    stats: Mapping[str, Any] | None,
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    caps = _member_caps(members, seed_blocks)
    if sum(caps.values()) < quota:
        raise ValueError(
            f"{layer} quota {quota} cannot satisfy the global 12.5% member cap"
        )
    weights = pfsp_weights(members, stats)

    if layer == "gold_train":
        hard = [member for member in members if member.get("hard_gold")]
        hard_floor = min(
            quota,
            int(math.ceil(seed_blocks * HARD_GOLD_MIN_TOTAL_RATIO - 1e-12)),
        )
        if sum(caps[member["id"]] for member in hard) < hard_floor:
            raise ValueError("hard Gold floor is infeasible under member/V76 caps")
        for _ in range(hard_floor):
            eligible = [member for member in hard if counts[member["id"]] < caps[member["id"]]]
            selected = _choose_fair(eligible, counts, weights)
            counts[selected["id"]] += 1

    while sum(counts.values()) < quota:
        eligible = [member for member in members if counts[member["id"]] < caps[member["id"]]]
        if not eligible:
            raise ValueError(f"no eligible {layer} opponent remains under caps")
        selected = _choose_fair(eligible, counts, weights)
        counts[selected["id"]] += 1
    return dict(counts)


def build_schedule(
    registry: Mapping[str, Any],
    stage: str,
    seed_start: int,
    seed_blocks: int,
    pool_seed: int,
    iteration: int = 0,
    stats: Mapping[str, Any] | None = None,
) -> list[SeedAssignment]:
    """Build a deterministic seed-block schedule; expand it for two seats later."""

    if seed_start < 0:
        raise ValueError("seed_start must be non-negative")
    stage_name = _normalise_stage(stage)
    quotas = layer_quotas(stage_name, seed_blocks)
    members_by_layer = {
        layer: [
            member for member in registry["members"]
            if member.get("training_enabled") and member.get("training_layer") == layer
        ]
        for layer in LAYER_ORDER
    }

    member_counts: dict[str, dict[str, int]] = {}
    for layer in LAYER_ORDER:
        member_counts[layer] = _allocate_layer(
            layer, quotas[layer], members_by_layer[layer], seed_blocks, stats
        )

    rng = random.Random(int(pool_seed) + 1_000_003 * int(iteration))
    slots: list[tuple[str, dict[str, Any]]] = []
    for layer in LAYER_ORDER:
        by_id = {member["id"]: member for member in members_by_layer[layer]}
        layer_slots = [
            (layer, by_id[member_id])
            for member_id, count in sorted(member_counts[layer].items())
            for _ in range(count)
        ]
        rng.shuffle(layer_slots)
        slots.extend(layer_slots)
    rng.shuffle(slots)

    return [
        SeedAssignment(
            seed=seed_start + offset,
            layer=layer,
            opponent_id=member["id"],
            opponent_sha256=member["sha256"],
            role=member["role"],
            lineage=member["lineage"],
            behavior_family=member["behavior_family"],
        )
        for offset, (layer, member) in enumerate(slots)
    ]


def expand_dual_seat(schedule: Iterable[SeedAssignment]) -> list[GameAssignment]:
    games: list[GameAssignment] = []
    for assignment in schedule:
        for candidate_seat in (0, 1):
            games.append(
                GameAssignment(
                    seed=assignment.seed,
                    candidate_seat=candidate_seat,
                    opponent_seat=1 - candidate_seat,
                    layer=assignment.layer,
                    opponent_id=assignment.opponent_id,
                    opponent_sha256=assignment.opponent_sha256,
                )
            )
    return games


def validate_schedule(
    registry: Mapping[str, Any], stage: str, schedule: Iterable[SeedAssignment]
) -> dict[str, Any]:
    rows = list(schedule)
    if not rows:
        raise ValueError("schedule is empty")
    if len({row.seed for row in rows}) != len(rows):
        raise ValueError("schedule contains duplicate seed blocks")
    allowed = {
        member["id"]: member
        for member in registry["members"]
        if member.get("training_enabled")
    }
    for row in rows:
        member = allowed.get(row.opponent_id)
        if member is None:
            raise ValueError(f"schedule contains disabled or unknown opponent: {row.opponent_id}")
        if member.get("gold_split") in {"dev", "blind"}:
            raise ValueError(f"schedule leaks Gold-{member['gold_split']}: {row.opponent_id}")
        if row.layer != member["training_layer"]:
            raise ValueError(f"schedule layer mismatch for {row.opponent_id}")

    total = len(rows)
    expected_quotas = layer_quotas(stage, total)
    layer_counts = Counter(row.layer for row in rows)
    if dict(layer_counts) != {key: value for key, value in expected_quotas.items() if value}:
        raise ValueError(f"layer quota mismatch: {dict(layer_counts)} != {expected_quotas}")
    member_counts = Counter(row.opponent_id for row in rows)
    general_cap = int(math.floor(total * MAX_MEMBER_RATIO + 1e-12))
    if any(count > general_cap for count in member_counts.values()):
        raise ValueError("single-opponent 12.5% cap exceeded")
    v76_count = sum(
        count for member_id, count in member_counts.items() if allowed[member_id].get("is_v76")
    )
    if v76_count > int(math.floor(total * MAX_V76_RATIO + 1e-12)):
        raise ValueError("V76 10% cap exceeded")
    hard_gold_count = sum(
        count for member_id, count in member_counts.items() if allowed[member_id].get("hard_gold")
    )
    required_hard = min(
        expected_quotas["gold_train"],
        int(math.ceil(total * HARD_GOLD_MIN_TOTAL_RATIO - 1e-12)),
    )
    if hard_gold_count < required_hard:
        raise ValueError("hard Gold minimum exposure not met")
    return {
        "seed_blocks": total,
        "games": total * 2,
        "stage": _normalise_stage(stage),
        "layer_counts": dict(layer_counts),
        "member_counts": dict(member_counts),
        "v76_seed_blocks": v76_count,
        "hard_gold_seed_blocks": hard_gold_count,
        "dual_seat_same_opponent": True,
    }


def schedule_report(
    registry: Mapping[str, Any], stage: str, schedule: Iterable[SeedAssignment]
) -> dict[str, Any]:
    rows = list(schedule)
    validation = validate_schedule(registry, stage, rows)
    return {
        "schema": "kaggriculture-v114-opponent-schedule-v1",
        "registry_path": registry.get("registry_path"),
        "registry_sha256": registry.get("registry_sha256"),
        **validation,
        "assignments": [asdict(row) for row in rows],
    }
