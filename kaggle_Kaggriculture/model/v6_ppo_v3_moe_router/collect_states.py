"""Collect reproducible *daily* PPO v3 decision states.

This is deliberately not a behaviour-cloning collector.  It writes state
snapshots that can later be replayed from the same seed and prefix by
``fork_counterfactuals.py``.  The replay recipe is the source agent,
opponent, seed, seat, fork step, and an observation/prefix fingerprint.
Counterfactual labels are never produced here.

The collector only serialises information observable to a Kaggle submission.
In particular it does not serialise an opponent's private inventory, private
cash, account identity, or online submission information.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from catalog import Catalog
from features import FEATURE_DIM, FEATURE_NAMES, SCHEMA_VERSION, encode_observation, update_history


SCHEMA_VERSION_STATES = "kaggriculture-ppo-v3-daily-states-1"
SPLIT_VERSION = "kaggriculture-ppo-v3-group-split-1"
DEFAULT_PRODUCTION = ("E_V1",)
DEFAULT_MARKET = ("M_NONE", "M_ANIMAL_HALF_TOPDAYS")


def _plain(value: Any) -> Any:
    """Convert Kaggle Struct/numpy values into canonical JSON values."""
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_plain(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def group_key(row: Mapping[str, Any]) -> str:
    """A split group intentionally excludes seat, so paired seats stay together."""
    # ``episode_id`` is human-readable and contains a seat suffix.  Use the
    # dedicated seat-free value below; otherwise paired games could leak into
    # different splits despite a seemingly correct group-split implementation.
    return "|".join(str(row.get(name, "")) for name in ("source", "strategy_family", "lineage", "episode_group_id", "seed"))


def split_for_group(key: str) -> str:
    bucket = int.from_bytes(hashlib.sha256((SPLIT_VERSION + "|" + key).encode("utf-8")).digest()[:8], "big") % 100
    return "train" if bucket < 80 else "validation" if bucket < 90 else "test"


def _day(obs: Mapping[str, Any], step: int) -> int:
    return int(obs.get("day", step // 24) or 0)


def _hour(obs: Mapping[str, Any], step: int) -> int:
    return int(obs.get("hour", step % 24) or 0)


def _opponent_factory(name: str, namespace: str):
    """Build deterministic, executable opponents for the D2 pilot.

    ``random`` is deliberately not accepted: the package random agent has
    process-local RNG state and would make a state replay recipe nonportable.
    More opponent families may be added only with an explicit deterministic
    factory and lineage manifest entry.
    """
    if name in {"v1", "adaptive"}:
        return Catalog(namespace + "_opponent").v1
    if name == "forced_low":
        return Catalog(namespace + "_opponent").low
    if name == "forced_high":
        return Catalog(namespace + "_opponent").high
    if name == "starter":
        from kaggle_environments.envs.kaggriculture import kaggriculture as kg
        return kg.starter_agent
    raise ValueError("unsupported non-reproducible or unknown opponent: %s" % name)


def _family(name: str) -> str:
    return {
        "v1": "adaptive_market",
        "adaptive": "adaptive_market",
        "forced_low": "route_template_low",
        "forced_high": "route_template_high",
        "starter": "official_starter",
    }.get(name, "unknown")


def _agent_from_catalog(catalog: Catalog, expert_id: str):
    if expert_id not in catalog.production:
        raise ValueError("unknown rollout source production expert: %s" % expert_id)
    # A source rollout uses exactly one complete production expert.  Market
    # choices are reserved for later counterfactual branches.
    return getattr(catalog, {"E_V1": "v1", "E_HIGH": "high"}[expert_id])


def _action_digest(action: Mapping[str, Any]) -> str:
    return stable_hash({"farmer": list(action.get("farmer") or []), "hands": list(action.get("hands") or []), "market": list(action.get("market") or [])})


def _run_episode(
    *,
    seed: int,
    seat: int,
    opponent_id: str,
    source_expert: str,
    start_day: int,
    end_day: int,
    namespace: str,
) -> list[dict[str, Any]]:
    from kaggle_environments import make

    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    candidate_catalog = Catalog(namespace + "_candidate")
    candidate = _agent_from_catalog(candidate_catalog, source_expert)
    opponent = _opponent_factory(opponent_id, namespace)
    history: dict[str, Any] = {}
    action_trace: list[dict[str, str]] = []
    records: list[dict[str, Any]] = []
    for step in range(719):
        env.state[0].observation.step = step
        env.state[1].observation.step = step
        obs = env.state[seat].observation
        day, hour = _day(obs, step), _hour(obs, step)
        if hour == 0:
            if start_day <= day <= end_day:
                feature = encode_observation(obs, history, previous_decision=(DEFAULT_PRODUCTION.index(source_expert), 0))
                episode_id = "d2-source-%s-%s-%d-%d" % (source_expert, opponent_id, int(seed), int(seat))
                meta = {
                    "source": source_expert,
                    "strategy_family": _family(opponent_id),
                    "lineage": "catalog-v1-routes-1",
                    "episode_id": episode_id,
                    "episode_group_id": "d2-source-%s-%s-%d" % (source_expert, opponent_id, int(seed)),
                    "seed": int(seed),
                    "seat": int(seat),
                }
                record = {
                    "schema": SCHEMA_VERSION_STATES,
                    **meta,
                    "pair_id": "d2-pair-%s-%s-%d" % (source_expert, opponent_id, int(seed)),
                    "opponent_id": opponent_id,
                    "day": int(day),
                    "step": int(step),
                    "state_id": "s_" + stable_hash({"meta": meta, "step": int(step), "obs": obs})[:24],
                    "state_hash": stable_hash(obs),
                    "prefix_hash": stable_hash(action_trace),
                    "features": feature.tolist(),
                    "feature_schema": SCHEMA_VERSION,
                    "eligible_production": list(DEFAULT_PRODUCTION),
                    "eligible_market": list(DEFAULT_MARKET),
                    "source_expert": source_expert,
                    "split_group": group_key(meta),
                    "split": split_for_group(group_key(meta)),
                }
                records.append(record)
            # Keep the immediately previous *day* even when that day is
            # outside the sampled window; otherwise day-3 market deltas would
            # be spuriously all-zero whenever collection starts at day 3.
            history = update_history(obs)
        own_action = candidate(obs)
        other_action = opponent(env.state[1 - seat].observation)
        actions = [own_action, other_action] if seat == 0 else [other_action, own_action]
        action_trace.append({"seat0": _action_digest(actions[0]), "seat1": _action_digest(actions[1])})
        env.step(actions)
    statuses = [str(state.status) for state in env.state]
    if statuses != ["DONE", "DONE"]:
        raise RuntimeError("source episode not done: %r" % (statuses,))
    return records


def _write_npz(records: list[Mapping[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    features = np.asarray([row["features"] for row in records], dtype=np.float32)
    if features.ndim != 2 or features.shape[1:] != (FEATURE_DIM,):
        raise ValueError("unexpected daily feature shape: %r" % (features.shape,))
    np.savez_compressed(
        output,
        features=features,
        pair_ids=np.asarray([str(row["pair_id"]) for row in records]),
        source=np.asarray([str(row["source"]) for row in records]),
        family=np.asarray([str(row["strategy_family"]) for row in records]),
        seed=np.asarray([int(row["seed"]) for row in records], dtype=np.int64),
        seat=np.asarray([int(row["seat"]) for row in records], dtype=np.int8),
        split=np.asarray([str(row["split"]) for row in records]),
        day=np.asarray([int(row["day"]) for row in records], dtype=np.int8),
        step=np.asarray([int(row["step"]) for row in records], dtype=np.int16),
        state_ids=np.asarray([str(row["state_id"]) for row in records]),
    )


def collect_states(
    *,
    seeds: Iterable[int],
    opponents: Iterable[str],
    output_dir: Path,
    source_expert: str = "E_V1",
    start_day: int = 3,
    end_day: int = 28,
) -> dict[str, Any]:
    """Write a replayable state JSONL, NPZ and group-split manifest."""
    if source_expert not in DEFAULT_PRODUCTION:
        raise ValueError("source_expert must be one of %r" % (DEFAULT_PRODUCTION,))
    if not 0 <= int(start_day) <= int(end_day) <= 29:
        raise ValueError("invalid daily collection window")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    seeds = [int(seed) for seed in seeds]
    opponents = [str(value) for value in opponents]
    for seed in seeds:
        for seat in (0, 1):
            for opponent_id in opponents:
                namespace = "collect_%s_%s_%d_%d" % (source_expert, opponent_id, seed, seat)
                rows = _run_episode(
                    seed=seed, seat=seat, opponent_id=opponent_id, source_expert=source_expert,
                    start_day=int(start_day), end_day=int(end_day), namespace=namespace,
                )
                records.extend(rows)
                print(json.dumps({"phase": "collect", "records": len(records), "seed": seed, "seat": seat, "opponent": opponent_id}), flush=True)
    # Exact states are never duplicated silently.  A duplicate means source
    # sampling did not provide additional information and should be visible.
    unique: dict[str, dict[str, Any]] = {}
    duplicate_count = 0
    for row in records:
        key = str(row["state_hash"])
        if key in unique:
            duplicate_count += 1
            continue
        unique[key] = row
    records = list(unique.values())
    records.sort(key=lambda row: (row["split"], row["seed"], row["seat"], row["opponent_id"], row["step"]))
    states_file = output_dir / "daily_states.jsonl"
    states_file.write_text("".join(canonical_json(row) + "\n" for row in records), encoding="utf-8")
    _write_npz(records, output_dir / "daily_states.npz")
    split_counts = {name: sum(row["split"] == name for row in records) for name in ("train", "validation", "test")}
    manifest = {
        "schema": SCHEMA_VERSION_STATES,
        "split_schema": SPLIT_VERSION,
        "feature_schema": SCHEMA_VERSION,
        "feature_dim": FEATURE_DIM,
        "feature_names": FEATURE_NAMES,
        "source_expert": source_expert,
        "opponents": opponents,
        "seeds": seeds,
        "day_window": [int(start_day), int(end_day)],
        "records": len(records),
        "raw_records": len(records) + duplicate_count,
        "exact_duplicate_states_removed": duplicate_count,
        "split_counts": split_counts,
        "files": {
            "daily_states_jsonl": states_file.name,
            "daily_states_npz": "daily_states.npz",
            "sha256_jsonl": hashlib.sha256(states_file.read_bytes()).hexdigest(),
        },
        "replay_contract": "reconstruct_from_seed_and_source_recipe; counterfactual runner must reject state_hash/prefix_hash mismatch",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def _seed_values(seed_start: int, count: int) -> list[int]:
    return [int(seed_start) + 7919 * index for index in range(int(count))]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, default=97300000)
    parser.add_argument("--seeds", type=int, default=2, help="pilot default; production should use a registered manifest")
    parser.add_argument("--opponents", nargs="+", default=["starter", "forced_low", "forced_high"])
    parser.add_argument("--source-expert", choices=DEFAULT_PRODUCTION, default="E_V1")
    parser.add_argument("--start-day", type=int, default=3)
    parser.add_argument("--end-day", type=int, default=28)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "data" / "d2_counterfactual" / "state_pilot")
    args = parser.parse_args()
    report = collect_states(
        seeds=_seed_values(args.seed_start, args.seeds), opponents=args.opponents, output_dir=args.output_dir,
        source_expert=args.source_expert, start_day=args.start_day, end_day=args.end_day,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
